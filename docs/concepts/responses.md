# Responses & Streaming

## Common Return Types

- `dict` / `list` -> JSON
- `str` -> text
- `bytes` -> binary
- `None` -> 204
- `(body, status)` / `(body, status, headers)`

## `Response`

```python
from bard import Response


async def binary():
    return Response(b"raw", headers={"content-type": "application/octet-stream"})
```

## `StreamingResponse`

Return `StreamingResponse` (or an async iterable of `bytes | str`) to stream output.

```python
import asyncio

from bard import StreamingResponse


async def chunks():
    for part in (b"a", b"b", b"c"):
        yield part
        await asyncio.sleep(0)


async def stream():
    return StreamingResponse(chunks())
```

Notes:

- Request-scoped DI cleanup runs after streaming completes or is cancelled.
- Request bodies and uploads are still buffered in memory.

## See Also

- [Memory & buffering constraints](../advanced/memory.md)
