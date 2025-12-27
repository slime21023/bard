from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any
from urllib.parse import parse_qs


class WebSocket:
    def __init__(
        self,
        scope: dict[str, Any],
        receive,
        send,
        state: dict[str, Any],
        *,
        exit_stack: AsyncExitStack | None = None,
    ) -> None:
        self.scope = scope
        self._receive = receive
        self._send = send
        self.state = state
        self.exit_stack = exit_stack
        self.di_cache: dict[object, Any] = {}
        self._headers: dict[str, str] | None = None
        self._query_params: dict[str, list[str]] | None = None
        self._accepted = False
        self._closed = False

    @property
    def path(self) -> str:
        return self.scope.get("path", "")

    @property
    def headers(self) -> dict[str, str]:
        if self._headers is None:
            headers: dict[str, str] = {}
            for key, value in self.scope.get("headers", []):
                headers[key.decode("latin-1").lower()] = value.decode("latin-1")
            self._headers = headers
        return self._headers

    @property
    def query_params(self) -> dict[str, list[str]]:
        if self._query_params is None:
            raw = self.scope.get("query_string", b"")
            parsed = parse_qs(raw.decode("latin-1"), keep_blank_values=True)
            self._query_params = parsed
        return self._query_params

    @property
    def accepted(self) -> bool:
        return self._accepted

    @property
    def closed(self) -> bool:
        return self._closed

    async def accept(self, *, headers: dict[str, str] | None = None, subprotocol: str | None = None) -> None:
        if self._accepted or self._closed:
            return
        message: dict[str, Any] = {"type": "websocket.accept"}
        if headers:
            message["headers"] = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
        if subprotocol:
            message["subprotocol"] = subprotocol
        await self._send(message)
        self._accepted = True

    async def close(self, *, code: int = 1000, reason: str | None = None) -> None:
        if self._closed:
            return
        message: dict[str, Any] = {"type": "websocket.close", "code": code}
        if reason:
            message["reason"] = reason
        await self._send(message)
        self._closed = True

    async def receive(self) -> dict[str, Any]:
        return await self._receive()

    async def send_text(self, data: str) -> None:
        await self._send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        await self._send({"type": "websocket.send", "bytes": data})

