# ASGI Integration

Bard is an ASGI app. You can wrap it to add cross-cutting behavior that is easier to express at the ASGI layer.

## Example: Add a Response Header for All HTTP Requests

```python
from bard import BardApp, Router


class HeaderWrapper:
    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            return await self._app(scope, receive, send)

        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-powered-by", b"bard"))
            await send(message)

        return await self._app(scope, receive, send_wrapper)


router = Router()
router.get("/", lambda: {"ok": True})
app = HeaderWrapper(BardApp(router))
```

