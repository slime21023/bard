# App

## `BardApp`

`BardApp(router, lifespan=None)` creates an ASGI app.

The constructor calls `router.compile()` immediately. Register routes and providers on the router before creating
the app to surface compilation errors early.

### Attributes

- `app.state`: a global `dict` available via `State` extractor and on `Request` / `WebSocket`.
  - Values are shared across all requests/connections.
  - Use `lifespan` to initialize and tear down resources.

### DI

- `app.provide(Type, provider, use_cache=True)`: register a type-based provider (same as `router.provide`).

### Middleware

- `app.add_middleware(middleware)`: HTTP middleware `async def mw(request: Request, call_next) -> Any`.
- `app.add_websocket_middleware(middleware)`: WebSocket middleware `async def mw(ws: WebSocket, call_next) -> Any`.

Order:

1. App-level middleware wraps router-level middleware.
2. Router-level middleware wraps the handler.

`call_next` takes no arguments and returns the downstream result (which is then normalized into a response).

### Error handling

- `app.add_exception_handler(exc_type, handler)`: map exceptions to normal return values.

Notes:

- The most specific matching handler is picked by walking `type(exc).__mro__`.
- `handler` may be sync or async.
- For HTTP requests, the handler return value is passed through normal response conversion.
- For WebSockets, the handler return value is ignored; perform any `ws.send_*` / `ws.close(...)` inside the handler.

### Lifespan

If `lifespan` is provided, it should be an `asynccontextmanager` taking `app`.

Lifecycle:

- On ASGI `lifespan.startup`, Bard enters the context manager and sends `lifespan.startup.complete`.
- On ASGI `lifespan.shutdown`, Bard exits it and sends `lifespan.shutdown.complete`.
- `TestClient` triggers startup/shutdown automatically when used as a context manager.
