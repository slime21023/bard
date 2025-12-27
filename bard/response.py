from __future__ import annotations

from collections.abc import AsyncIterable, Iterable
from typing import Any

from .utils import encode_json


class Response:
    def __init__(
        self,
        body: bytes,
        status: int = 200,
        headers: dict[str, str] | list[tuple[bytes, bytes]] | None = None,
        media_type: str | None = "text/plain; charset=utf-8",
    ) -> None:
        self.status = status
        self.body = body
        self.headers = _normalize_headers(headers)
        if media_type:
            self._ensure_content_type(media_type)

    def _ensure_content_type(self, media_type: str) -> None:
        lowered = [key.lower() for key, _ in self.headers]
        if b"content-type" not in lowered:
            self.headers.append((b"content-type", media_type.encode("latin-1")))

    async def __call__(self, send) -> None:
        await send({"type": "http.response.start", "status": self.status, "headers": self.headers})
        await send({"type": "http.response.body", "body": self.body})


class StreamingResponse:
    def __init__(
        self,
        body: AsyncIterable[bytes | str] | Iterable[bytes | str],
        status: int = 200,
        headers: dict[str, str] | list[tuple[bytes, bytes]] | None = None,
        media_type: str | None = "application/octet-stream",
    ) -> None:
        self.status = status
        self.body = body
        self.headers = _normalize_headers(headers)
        self.media_type = media_type
        if media_type:
            self._ensure_content_type(media_type)

    def _ensure_content_type(self, media_type: str) -> None:
        lowered = [key.lower() for key, _ in self.headers]
        if b"content-type" not in lowered:
            self.headers.append((b"content-type", media_type.encode("latin-1")))

    async def __call__(self, send) -> None:
        await send({"type": "http.response.start", "status": self.status, "headers": self.headers})
        if _is_async_iterable(self.body):
            async for chunk in self.body:
                await send({"type": "http.response.body", "body": _coerce_chunk(chunk), "more_body": True})
        else:
            for chunk in self.body:
                await send({"type": "http.response.body", "body": _coerce_chunk(chunk), "more_body": True})
        await send({"type": "http.response.body", "body": b"", "more_body": False})


def to_response(result: Any) -> Response | StreamingResponse:
    if isinstance(result, (Response, StreamingResponse)):
        return result

    status = 200
    headers = None

    if isinstance(result, tuple):
        if len(result) == 2:
            result, status = result
        elif len(result) == 3:
            result, status, headers = result
        else:
            raise ValueError("Response tuple must be (body, status) or (body, status, headers)")

    if isinstance(result, StreamingResponse):
        if status == 200 and headers is None:
            return result
        return StreamingResponse(result.body, status=status, headers=headers, media_type=result.media_type)

    if result is None:
        return Response(b"", status=204, media_type=None, headers=headers)
    if isinstance(result, bytes):
        return Response(result, status=status, media_type="application/octet-stream", headers=headers)
    if isinstance(result, str):
        return Response(result.encode("utf-8"), status=status, headers=headers)
    if _is_async_iterable(result) or _is_iterable_stream(result):
        return StreamingResponse(result, status=status, headers=headers)

    body = encode_json(result)
    return Response(body, status=status, media_type="application/json", headers=headers)


def _normalize_headers(
    headers: dict[str, str] | list[tuple[bytes, bytes]] | None,
) -> list[tuple[bytes, bytes]]:
    if headers is None:
        return []
    if isinstance(headers, dict):
        return [(key.encode("latin-1"), value.encode("latin-1")) for key, value in headers.items()]
    normalized: list[tuple[bytes, bytes]] = []
    for key, value in headers:
        if isinstance(key, str):
            key = key.encode("latin-1")
        if isinstance(value, str):
            value = value.encode("latin-1")
        normalized.append((key, value))
    return normalized


def _is_async_iterable(value: Any) -> bool:
    return hasattr(value, "__aiter__")


def _is_iterable_stream(value: Any) -> bool:
    if isinstance(value, (bytes, str, dict, list, tuple)):
        return False
    return isinstance(value, Iterable)


def _coerce_chunk(chunk: bytes | str) -> bytes:
    if isinstance(chunk, bytes):
        return chunk
    return chunk.encode("utf-8")
