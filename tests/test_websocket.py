from __future__ import annotations

import asyncio
from typing import Annotated

from bard import BardApp, Header, Path, Query, Router, WebSocket


def test_websocket_route_accepts_and_sends():
    async def ws_handler(ws: WebSocket):
        await ws.send_text("hi")
        await ws.close(code=1000)

    router = Router()
    router.websocket("/ws", ws_handler)
    app = BardApp(router)

    async def run_ws():
        messages = []

        async def receive():
            return {"type": "websocket.connect"}

        async def send(message):
            messages.append(message)

        scope = {"type": "websocket", "asgi": {"version": "3.0"}, "path": "/ws", "headers": [], "query_string": b""}
        await app(scope, receive, send)
        return messages

    sent = asyncio.run(run_ws())

    assert sent[0]["type"] == "websocket.accept"
    assert sent[1]["type"] == "websocket.send"
    assert sent[1]["text"] == "hi"
    assert sent[2]["type"] == "websocket.close"


def test_websocket_extractors_and_path_params_work():
    async def ws_handler(
        ws: WebSocket,
        user_id: Annotated[str, Path],
        q: Annotated[str, Query],
        agent: Annotated[str, Header("user-agent")],
    ):
        await ws.send_text(f"{user_id}:{q}:{agent}")

    router = Router()
    router.websocket("/ws/{user_id}", ws_handler)
    app = BardApp(router)

    async def run_ws():
        messages = []

        async def receive():
            return {"type": "websocket.connect"}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "path": "/ws/alice",
            "headers": [(b"user-agent", b"Probe")],
            "query_string": b"q=hello",
        }
        await app(scope, receive, send)
        return messages

    sent = asyncio.run(run_ws())

    assert sent[0]["type"] == "websocket.accept"
    assert sent[1]["type"] == "websocket.send"
    assert sent[1]["text"] == "alice:hello:Probe"
