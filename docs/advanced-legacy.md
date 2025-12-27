# Advanced Patterns (Legacy Copy)

This page is kept for compatibility but is no longer maintained as a single document.
Use the split advanced pages instead:

- [Overview](advanced/index.md)
- [Routing](advanced/routing.md)
- [Conversion](advanced/conversion.md)
- [Memory](advanced/memory.md)
- [Lifespan](advanced/lifespan.md)
- [ASGI](advanced/asgi.md)
- [TestClient](advanced/testclient.md)
- [Composition](advanced/composition.md)

This page collects patterns used when building higher-level ASGI frameworks on
top of Bard, plus runtime constraints that matter for framework authors. Each
Python example is a complete script you can copy into `app.py` and run with
`uv run python app.py` unless noted.

## ASGI Support and Limitations

- Supports `http`, `lifespan`, and `websocket` scopes.
- Supports WebSocket routing via `Router.websocket(...)`.
- Response bodies can be streamed via `StreamingResponse` (request bodies are still buffered).
- Supports app-level and router-level middleware, plus custom exception handlers.

Example:

```python
import uvicorn

from bard import BardApp, Router


async def root():
    return {"ok": True}


router = Router()
router.get("/", root)
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## Routing Precedence and Matching

Static segments win over parameter matches. `HEAD` falls back to `GET`.

```python
from typing import Annotated

from bard import BardApp, Path, Router, TestClient


async def me():
    return {"route": "me"}


async def by_id(user_id: Annotated[int, Path]):
    return {"route": "id", "id": user_id}


router = Router()
router.get("/users/me", me)
router.get("/users/{user_id}", by_id)
app = BardApp(router)


if __name__ == "__main__":
    with TestClient(app) as client:
        assert client.get("/users/me").json()["route"] == "me"
        assert client.get("/users/42").json()["id"] == 42
        assert client.request("HEAD", "/users/me").status == 200
    print("ok")
```

## Extractor Conversion Rules

- Missing required inputs return 422 unless a default or `Optional` is provided.
- Lists accept repeated values (`?tag=a&tag=b`).
- Booleans accept `true/false/1/0/yes/no/on/off`.

```python
from typing import Annotated

from bard import BardApp, Query, Router, TestClient


async def search(
    page: Annotated[int, Query],
    debug: Annotated[bool, Query] = False,
    tags: Annotated[list[str] | None, Query("tag")] = None,
):
    return {"page": page, "debug": debug, "tags": tags or []}


router = Router()
router.get("/search", search)
app = BardApp(router)


if __name__ == "__main__":
    with TestClient(app) as client:
        resp = client.get("/search?page=2&debug=true&tag=alpha&tag=beta")
        assert resp.json() == {"page": 2, "debug": True, "tags": ["alpha", "beta"]}
    print("ok")
```

## Request and Response Behavior

Bodies are cached after the first read. Response normalization covers common
Python return types.

```python
from bard import BardApp, Request, Response, Router, TestClient


async def raw(request: Request):
    body = await request.body()
    again = await request.body()
    return {"size": len(body), "cached": body == again}


async def binary():
    return Response(b"raw", headers={"content-type": "application/octet-stream"})


async def empty():
    return None


router = Router()
router.post("/raw", raw)
router.get("/binary", binary)
router.get("/empty", empty)
app = BardApp(router)


if __name__ == "__main__":
    with TestClient(app) as client:
        resp = client.post("/raw", body=b"hello")
        assert resp.json()["cached"] is True
        assert client.get("/empty").status == 204
    print("ok")
```

## Form and File Memory Notes

Form parsing is eager; uploads are held in memory via `UploadFile.content`.
For large uploads, consider terminating or proxying before Bard.

## Middleware and Dependency Injection Design

Bard ships built-in app-level and router-level middleware, plus dependency injection
with request-scoped cleanup. The patterns below are still useful if you want to
wrap Bard as a component inside a larger ASGI system.

### Optional ASGI middleware wrapper

This pattern composes async functions around the app and is compatible with
any ASGI server:

```python
import uvicorn

from bard import BardApp, Router


class MiddlewareStack:
    def __init__(self, app, middlewares):
        self._app = app
        self._middlewares = middlewares

    async def __call__(self, scope, receive, send):
        handler = self._app
        for mw in reversed(self._middlewares):
            handler = mw(handler)
        await handler(scope, receive, send)


def timing_middleware(next_app):
    async def app(scope, receive, send):
        if scope.get("type") != "http":
            return await next_app(scope, receive, send)
        return await next_app(scope, receive, send)

    return app


def header_middleware(next_app):
    async def app(scope, receive, send):
        if scope.get("type") != "http":
            return await next_app(scope, receive, send)

        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append((b"x-powered-by", b"bard"))
            await send(message)

        return await next_app(scope, receive, send_wrapper)

    return app


router = Router()
router.get("/", lambda: {"ok": True})
app = BardApp(router)
stack = MiddlewareStack(app, [timing_middleware, header_middleware])


if __name__ == "__main__":
    uvicorn.run(stack, host="127.0.0.1", port=8000)
```

### Simple dependency injection via `State`

For a framework-style DI container, register dependencies at startup and
inject them with `State` extractors. This keeps handlers pure and testable.

```python
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn

from bard import BardApp, Router, State


class Container:
    def __init__(self):
        self.db = "db:ready"
        self.cache = "cache:ready"


@asynccontextmanager
async def lifespan(app):
    app.state["container"] = Container()
    yield


async def health(container: Annotated[Container, State("container")]):
    return {"db": container.db, "cache": container.cache}


router = Router()
router.get("/health", health)
app = BardApp(router, lifespan=lifespan)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## Exception Handling and Response Rendering Pipeline

Bard converts handler return values into a `Response`. For a framework,
centralize exception handling and rendering to standardize payloads.

### Global exception handler

```python
import uvicorn

from bard import BardApp, HTTPError, Router


class AppError(Exception):
    def __init__(self, code: str, detail: str, status: int = 400):
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status


class ErrorHandlingApp:
    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        try:
            await self._app(scope, receive, send)
        except AppError as exc:
            await self._send_json(send, exc.status, {"error": exc.code, "detail": exc.detail})
        except HTTPError as exc:
            await self._send_json(send, exc.status_code, {"detail": exc.detail})

    async def _send_json(self, send, status, payload):
        body = (
            b'{"error":"' + payload.get("error", "").encode("utf-8") + b'","detail":"' +
            payload.get("detail", "").encode("utf-8") + b'"}'
        ) if "error" in payload else (
            b'{"detail":"' + payload.get("detail", "").encode("utf-8") + b'"}'
        )
        await send({"type": "http.response.start", "status": status, "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": body})


async def fail():
    raise AppError("invalid", "bad input", status=422)


router = Router()
router.get("/fail", fail)
app = ErrorHandlingApp(BardApp(router))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

### Response rendering as a policy layer

If you want consistent envelopes, wrap handlers instead of touching the core:

```python
import uvicorn

from bard import BardApp, Router


def envelope(handler):
    async def wrapped(*args, **kwargs):
        result = handler(*args, **kwargs)
        if hasattr(result, "__await__"):
            result = await result
        return {"data": result, "ok": True}

    return wrapped


router = Router()
router.get("/health", envelope(lambda: {"status": "ok"}))
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## WebSocket and Streaming Gaps

Current limitations:

- WebSocket support is minimal (no higher-level receive loop helpers beyond `ws.receive()`).
- HTTP request bodies and uploads are buffered in memory.

### WebSocket extension strategy

Use `Router.websocket("/ws", handler)` and the injected `WebSocket` object. Higher-level
frameworks can wrap `WebSocket` to add message parsing, ping/pong, and structured events.

```python
import uvicorn

from bard import BardApp, Router, WebSocket


async def ws_handler(ws: WebSocket):
    await ws.send_text("hello")
    await ws.close()


router = Router()
router.websocket("/ws", ws_handler)
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

### Streaming extension strategy

Return `StreamingResponse` (or an async iterable) and keep cleanup in mind: request-scoped
DI resources are cleaned up after streaming completes or is cancelled.

```python
import asyncio
import uvicorn

from bard import BardApp, Router, StreamingResponse


async def stream_handler():
    async def chunks():
        for part in (b"part-1\n", b"part-2\n", b"part-3\n"):
            yield part
            await asyncio.sleep(0)

    return StreamingResponse(chunks(), media_type="text/plain; charset=utf-8")


router = Router()
router.get("/stream", stream_handler)
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## TestClient and Event Loops

`TestClient` creates its own event loop and cannot run inside an active loop.
If you are already inside `asyncio`, run the app with a real server instead.

## Composition and Reuse

Organize larger apps by grouping route registration into helpers.

```python
import uvicorn

from bard import BardApp, Router


def add_health_routes(router: Router) -> None:
    router.get("/health", lambda: {"ok": True})


def add_version_routes(router: Router) -> None:
    router.get("/version", lambda: {"version": "0.1"})


router = Router()
add_health_routes(router)
add_version_routes(router)
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## Lifespan for Resources

Use lifespan to initialize and tear down resources and expose them via `State`.

```python
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn

from bard import BardApp, Router, State


@asynccontextmanager
async def lifespan(app):
    app.state["cache"] = "ready"
    yield
    app.state["cache"] = "closed"


async def health(cache: Annotated[str, State("cache")]):
    return {"cache": cache}


router = Router()
router.get("/health", health)
app = BardApp(router, lifespan=lifespan)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## Error Boundaries

Raise `HTTPError` for explicit failures; any other exception becomes 500.

```python
from bard import BardApp, HTTPError, Router, TestClient


async def guarded():
    raise HTTPError(403, "forbidden")


router = Router()
router.get("/guarded", guarded)
app = BardApp(router)


if __name__ == "__main__":
    with TestClient(app) as client:
        resp = client.get("/guarded")
        assert resp.status == 403
    print("ok")
```

## Escape Hatch with `Request`

Use `Request` when you need access to the raw ASGI surface.

```python
from bard import BardApp, Request, Router, TestClient


async def headers(request: Request):
    return {"keys": sorted(request.headers)}


router = Router()
router.get("/headers", headers)
app = BardApp(router)


if __name__ == "__main__":
    with TestClient(app) as client:
        resp = client.get("/headers")
        assert resp.status == 200
    print("ok")
```

## Building Your Own Abstractions

Most higher-level features can be built by:

1. Creating helper functions that register routes.
2. Reusing extractors for strong typing.
3. Delegating raw access to `Request` for edge cases.
