# Middleware

## HTTP middleware

Signature:

```python
async def middleware(request, call_next):
    result = await call_next()
    return result
```

`call_next` takes no arguments and returns the downstream handler result.
The middleware return value is normalized the same way as handler return values (see [Responses](responses.md)).

Applied order:

1. `app.add_middleware(...)`
2. `router.add_middleware(...)`
3. handler

Notes:

- Middleware is executed per request.
- Router-level middleware applies only to routes registered on that router (including included routes).
- App-level middleware wraps router-level middleware.

## WebSocket middleware

Signature:

```python
async def middleware(ws, call_next):
    result = await call_next()
    return result
```

Applied order:

1. `app.add_websocket_middleware(...)`
2. `router.add_websocket_middleware(...)`
3. handler

Notes:

- WebSocket middleware should usually perform side effects on `ws` (send/close).
- The return value of a WebSocket handler is ignored by the server; treat the result as informational only.
