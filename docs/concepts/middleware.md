# Middleware

Middleware wraps handler execution:

```python
from bard import Request


async def middleware(request: Request, call_next):
    result = await call_next()
    return result
```

## App-level Middleware

```python
from bard import BardApp, Request, Router


async def add_header(request: Request, call_next):
    result = await call_next()
    return result, 200, {"x-mw": "1"}


router = Router()
router.get("/", lambda: {"ok": True})
app = BardApp(router)
app.add_middleware(add_header)
```

## Router-level Middleware

```python
from bard import Request, Router


async def child_only(request: Request, call_next):
    result = await call_next()
    return result, 200, {"x-scope": "child"}


child = Router()
child.add_middleware(child_only)
```

## Order

- App-level middleware wraps router-level middleware.
- Router-level middleware wraps the handler.

## See Also

- [ASGI integration patterns](../advanced/asgi.md)
