# WebSocket

## Connection closes immediately

Checklist:

- Confirm you registered a WebSocket route via `router.websocket("/path", handler)`.
- Confirm the ASGI server is actually sending a `websocket.connect` event for that path.
- Bard closes unknown WebSocket routes with code `1000`.

## Unexpected `1011` close codes

Bard closes with `1011` if an unhandled exception escapes your WebSocket handler.

Fixes:

- Add an exception handler and perform close/send logic inside it:

```python
from bard import BardApp, WebSocket

async def on_error(ws: WebSocket, exc: BaseException):
    await ws.close(code=1011, reason=str(exc))

app.add_exception_handler(Exception, on_error)
```

- Validate your handler doesn't call `ws.accept()`/`ws.close()` multiple times (they are idempotent, but logic bugs
  can still cause unexpected flows).

## Using extractors with WebSockets

WebSocket handlers can still use `Path`, `Query`, `Header`, and `State` because Bard injects a `WebSocket` object that
exposes `headers`, `query_params`, and `state`.

Notes:

- `Json` / `Form` / `File` extractors are HTTP-only.
- Prefer `await ws.receive()` for raw ASGI messages; build your own parsing layer on top.

