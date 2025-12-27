# Bard

Bard is a small ASGI framework focused on type-driven extractors and startup-time compilation.

## Quick Start

Install (recommended: `uv`):

```bash
uv sync
```

Run the demo app:

```bash
uv run python examples/quickstart.py
```

Try it:

```bash
curl http://127.0.0.1:8000/
curl -X POST http://127.0.0.1:8000/users \
  -H "content-type: application/json" \
  -d "{\"username\":\"demo\",\"email\":\"demo@example.com\"}"
```

More runnable examples are in `examples/README.md`.

## Extractors

```python
from typing import Annotated

from bard import Header, Json, Query, Router, State


async def search(
    q: Annotated[str, Query],
    agent: Annotated[str, Header("user-agent")],
    db: Annotated[str, State("db")],
):
    return {"q": q, "agent": agent, "db": db}
```

## Dependencies (DI)

Register a type-based provider and use the type directly in your handler signature.

```python
from contextlib import contextmanager
from typing import Annotated

from bard import BardApp, Depends, Router


class Database:
    def query(self) -> str:
        return "ok"

    def close(self) -> None:
        pass


@contextmanager
def provide_db():
    db = Database()
    yield db
    db.close()  # optional: if you have it


async def read(db: Database):
    return {"status": db.query()}


async def override(db: Annotated[Database, Depends(provide_db)]):
    return {"status": db.query()}


router = Router()
router.provide(Database, provide_db)
router.get("/read", read)
router.get("/override", override)
app = BardApp(router)
```

Providers may return a plain object, a `contextmanager` / `asynccontextmanager`, or an object
with `close()` / `aclose()`. Bard will clean up request-scoped dependencies automatically.

## Middleware

Register app-level HTTP middleware:

```python
from bard import BardApp, Request, Router


async def add_header(request: Request, call_next):
    result = await call_next()
    return result, 200, {"x-middleware": "1"}


router = Router()
app = BardApp(router)
app.add_middleware(add_header)
```

## WebSocket

```python
from bard import BardApp, Router, WebSocket


async def ws_handler(ws: WebSocket):
    await ws.send_text("hello")
    await ws.close()


router = Router()
router.websocket("/ws", ws_handler)
app = BardApp(router)
```

## Streaming

```python
from bard import BardApp, Router, StreamingResponse


async def gen():
    yield b"a"
    yield b"b"


async def stream():
    return StreamingResponse(gen())


router = Router()
router.get("/stream", stream)
app = BardApp(router)
```

## Forms & Files

Use `Form` for form fields and `File` for uploads. URL-encoded and multipart
requests are supported.

```python
from typing import Annotated

from bard import File, Form, FormData, Router, UploadFile


async def submit(name: Annotated[str, Form]):
    return {"name": name}


async def upload(file: Annotated[UploadFile, File("file")]):
    return {"filename": file.filename, "size": len(file.content)}


async def capture(form: Annotated[FormData, Form]):
    return {"fields": form.fields, "files": list(form.files)}


router = Router()
router.post("/submit", submit)
router.post("/upload", upload)
router.post("/capture", capture)
```

Try it:

```bash
curl -X POST http://127.0.0.1:8000/submit \
  -H "content-type: application/x-www-form-urlencoded" \
  -d "name=bard"

curl -X POST http://127.0.0.1:8000/upload \
  -F "file=@README.md"
```

## Testing

Use the in-process `TestClient` without running a server. It triggers ASGI lifespan startup/shutdown by default.

Run the test suite:

```bash
uv run python -m pytest
```

```python
from typing import Annotated

from bard import BardApp, Json, Router, TestClient


async def echo(payload: Annotated[dict, Json]):
    return {"received": payload}


router = Router()
router.post("/echo", echo)
app = BardApp(router)

with TestClient(app) as client:
    resp = client.post("/echo", json={"hello": "bard"})
    assert resp.status == 200
    assert resp.json()["received"]["hello"] == "bard"
```
