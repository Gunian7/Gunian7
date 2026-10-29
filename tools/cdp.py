"""Minimal CDP client so we can drive the already-running headless Chrome.

The Hermes browser harness cannot auto-launch on this machine (it looks for
/usr/bin/google-chrome), but a headless Chrome is up with --remote-debugging-port=0.
We discover its port from DevToolsActivePort and talk to it directly.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx
import websockets

PROFILE = Path(os.path.expanduser("~/AppData/Local/hermes/browser-profile/chrome"))


def devtools_port() -> int:
    f = PROFILE / "DevToolsActivePort"
    if not f.exists():
        raise RuntimeError(f"no DevToolsActivePort in {PROFILE}")
    return int(f.read_text().splitlines()[0].strip())


def targets(port: int | None = None) -> list[dict]:
    port = port or devtools_port()
    r = httpx.get(f"http://127.0.0.1:{port}/json/list", timeout=10)
    return r.json()


class Tab:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self._id = 0
        self._ws = None
        self._loop = None

    async def __aenter__(self):
        self._ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024)
        return self

    async def __aexit__(self, *exc):
        await self._ws.close()

    async def send(self, method: str, **params):
        self._id += 1
        mid = self._id
        await self._ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=60))
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    async def eval(self, expr: str, await_promise: bool = True):
        r = await self.send(
            "Runtime.evaluate",
            expression=expr,
            returnByValue=True,
            awaitPromise=await_promise,
            userGesture=True,
        )
        res = r.get("result", {})
        if r.get("exceptionDetails"):
            return {"__error__": r["exceptionDetails"].get("text"), "detail": str(res)[:400]}
        return res.get("value")

    async def goto(self, url: str, wait: float = 3.0):
        await self.send("Page.navigate", url=url)
        await asyncio.sleep(wait)

    async def shot(self, path: str, full: bool = True):
        r = await self.send("Page.captureScreenshot", format="png", captureBeyondViewport=full)
        import base64

        Path(path).write_bytes(base64.b64decode(r["data"]))
        return path


def pick(starts: str | None = None) -> Tab:
    ts = targets()
    pages = [t for t in ts if t.get("type") == "page"]
    if starts:
        pages = [t for t in pages if t["url"].startswith(starts)] or pages
    if not pages:
        raise RuntimeError(f"no page targets: {[(t.get('type'), t.get('url')) for t in ts]}")
    return Tab(pages[0]["webSocketDebuggerUrl"])


async def create_page(url: str = "about:blank") -> Tab:
    """Open a new tab through the browser-level endpoint (the harness keeps zero pages)."""
    port = devtools_port()
    ver = httpx.get(f"http://127.0.0.1:{port}/json/version", timeout=10).json()
    async with websockets.connect(ver["webSocketDebuggerUrl"], max_size=20 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"id": 1, "method": "Target.createTarget", "params": {"url": url}}))
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
            if msg.get("id") == 1:
                target_id = msg["result"]["targetId"]
                break
    for _ in range(20):
        for t in targets(port):
            if t.get("id") == target_id and t.get("webSocketDebuggerUrl"):
                return Tab(t["webSocketDebuggerUrl"])
        await asyncio.sleep(0.3)
    raise RuntimeError("created target never exposed a websocket url")


async def page(url: str = "about:blank") -> Tab:
    """Reuse an existing tab (preferring one on `url`'s host) or create a fresh one."""
    host = url.split("/")[2] if "//" in url else ""
    ts = [t for t in targets() if t.get("type") == "page"]
    if host:
        same = [t for t in ts if host in (t.get("url") or "")]
        if same:
            return Tab(same[0]["webSocketDebuggerUrl"])
    if ts:
        return Tab(ts[0]["webSocketDebuggerUrl"])
    return await create_page(url)


async def run(url: str, expr: str):
    async with pick() as tab:
        await tab.goto(url, wait=4)
        print(json.dumps(await tab.eval(expr), ensure_ascii=False, indent=1)[:3000])


if __name__ == "__main__":
    print("port:", devtools_port())
    for t in targets():
        print(t.get("type"), "|", (t.get("url") or "")[:100])
