# Bard Documentation

Bard is a small ASGI framework focused on type-driven extractors and startup-time compilation.

## Quickstart

## Minimal App

Save as `app.py`:

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

Run:

```bash
uv run python app.py
```

## Quick Links

- [API Reference](reference/index.md)
- [Advanced Overview](advanced/index.md)
- [Troubleshooting](troubleshooting/index.md)

## Common Tasks

- Register routes: [Routing & Subrouters](concepts/routing.md)
- Parse inputs via `Annotated`: [Extractors](concepts/extractors.md)
- Add DI providers: [Dependencies (DI)](concepts/di.md)
- Add middleware: [Middleware](concepts/middleware.md)
- Return responses / streaming: [Responses & Streaming](concepts/responses.md)
- WebSocket endpoints: [WebSocket](concepts/websocket.md)
- Write tests: [Testing](howto/testing.md)
- Handle errors: [Error Handling](howto/errors.md)
