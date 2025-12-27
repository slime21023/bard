from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .utils import decode_json, encode_json


@dataclass
class TestResponse:
    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return decode_json(self.body, Any)


class TestClient:
    __test__ = False

    def __init__(self, app) -> None:
        self.app = app
        self._loop = None
        self._previous_loop = None

    def __enter__(self):
        self._loop = asyncio.new_event_loop()
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            self._previous_loop = None
        else:
            raise RuntimeError("TestClient cannot run inside an active event loop")
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self.app.startup())
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._loop is None:
            return
        self._loop.run_until_complete(self.app.shutdown())
        self._loop.close()
        asyncio.set_event_loop(self._previous_loop)
        self._loop = None
        self._previous_loop = None

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json: Any | None = None,
        body: bytes | None = None,
    ) -> TestResponse:
        if json is not None and body is not None:
            raise ValueError("Provide json or body, not both")
        if json is not None:
            body = encode_json(json)
            headers = headers or {}
            headers.setdefault("content-type", "application/json")
        if self._loop is None:
            return asyncio.run(self._request_async(method, path, headers=headers, body=body))
        return self._loop.run_until_complete(self._request_async(method, path, headers=headers, body=body))

    def get(self, path: str, **kwargs) -> TestResponse:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> TestResponse:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> TestResponse:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> TestResponse:
        return self.request("DELETE", path, **kwargs)

    async def _request_async(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None,
        body: bytes | None,
    ) -> TestResponse:
        parsed = urlsplit(path)
        headers = headers or {}
        headers_list = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "method": method.upper(),
            "path": parsed.path or "/",
            "query_string": parsed.query.encode("latin-1"),
            "headers": headers_list,
            "http_version": "1.1",
        }
        body_bytes = body or b""
        body_sent = False
        messages = []

        async def receive():
            nonlocal body_sent
            if body_sent:
                await asyncio.sleep(0)
                return {"type": "http.request", "body": b"", "more_body": False}
            body_sent = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        async def send(message):
            messages.append(message)

        await self.app(scope, receive, send)

        status = 500
        resp_headers: dict[str, str] = {}
        body_parts: list[bytes] = []
        for message in messages:
            if message["type"] == "http.response.start":
                status = message["status"]
                for key, value in message.get("headers", []):
                    resp_headers[key.decode("latin-1")] = value.decode("latin-1")
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))

        return TestResponse(status=status, headers=resp_headers, body=b"".join(body_parts))
