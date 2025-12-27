# WebSocket

`WebSocket` is injected into WebSocket handlers and provides:

- `await ws.accept(headers=None, subprotocol=None)`
- `await ws.receive()` (raw ASGI message)
- `await ws.send_text(str)` / `await ws.send_bytes(bytes)`
- `await ws.close(code=1000, reason=None)`

It also exposes:

- `ws.path`
- `ws.headers`
- `ws.query_params`
- `ws.state`

## Connection lifecycle

- Bard calls `ws.accept()` automatically before invoking your handler.
- If your handler returns without closing, Bard closes with code `1000`.
- If an unhandled exception escapes the handler, Bard closes with code `1011` (unless an exception handler swallows it).

## Headers and query params

- `ws.headers` lowercases keys and decodes as latin-1.
- `ws.query_params` returns `dict[str, list[str]]` (same parsing behavior as `Request.query_params`).
