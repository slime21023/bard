from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

from contextlib import AsyncExitStack

from .form import FormData, parse_form


class Request:
    def __init__(
        self,
        scope: dict[str, Any],
        receive,
        state: dict[str, Any],
        *,
        exit_stack: AsyncExitStack | None = None,
    ):
        self.scope = scope
        self._receive = receive
        self.state = state
        self.exit_stack = exit_stack
        self.di_cache: dict[object, Any] = {}
        self._body: bytes | None = None
        self._headers: dict[str, str] | None = None
        self._query_params: dict[str, list[str]] | None = None
        self._form: FormData | None = None
        self._form_parsed = False

    @property
    def method(self) -> str:
        return self.scope.get("method", "")

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

    async def body(self) -> bytes:
        if self._body is not None:
            return self._body
        chunks: list[bytes] = []
        while True:
            message = await self._receive()
            message_type = message.get("type")
            if message_type == "http.disconnect":
                break
            if message_type != "http.request":
                continue
            chunk = message.get("body", b"")
            if chunk:
                chunks.append(chunk)
            if not message.get("more_body", False):
                break
        self._body = b"".join(chunks)
        return self._body

    async def form(self) -> FormData:
        if self._form_parsed:
            return self._form or FormData()
        content_type = self.headers.get("content-type", "")
        body = await self.body()
        if not content_type:
            self._form = FormData()
        else:
            self._form = parse_form(body, content_type)
        self._form_parsed = True
        return self._form
