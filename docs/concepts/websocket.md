# WebSocket

Register a WebSocket route:

```python
from bard import Router, WebSocket


async def ws_handler(ws: WebSocket):
    await ws.send_text("hello")
    await ws.close()


router = Router()
router.websocket("/ws", ws_handler)
```

`WebSocket` basics:

- `await ws.accept()`
- `await ws.receive()` (raw ASGI message)
- `await ws.send_text(...)` / `await ws.send_bytes(...)`
- `await ws.close(code=1000)`

Extractors (`Path`, `Query`, `Header`, `State`) work the same way as HTTP handlers.

