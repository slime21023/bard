# Development Guide

Notes for contributors working on Bard.

## Setup

We use `uv`:

```bash
uv sync --group dev
```

## Layout

- `bard/`: framework code
  - `app.py`: ASGI entrypoint and lifespan flow
  - `di.py`: dependency injection + cleanup helpers
  - `router.py`: route registration and matching
  - `handler.py`: extractor compilation
  - `request.py`: request wrapper + form parsing entry
  - `response.py`: response normalization
  - `websocket.py`: WebSocket wrapper
  - `form.py`: form and file parsing
  - `utils.py`: conversion and JSON helpers
- `tests/`: unit tests (full coverage)
- `examples/`: runnable demos
- `docs/`: developer and API docs

## Run Tests

```bash
uv run pytest
uv run pytest --cov=bard --cov-report=term-missing
```

## Run Examples

```bash
uv run python examples/quickstart.py
uv run python examples/forms_files.py
uv run python examples/dependencies.py
uv run python examples/middleware.py
uv run python examples/subrouter.py
uv run python examples/streaming.py
uv run python examples/websocket.py
```

## Request Flow

1. `Router.add_route()` registers routes and compiles handler resolvers (DI may be finalized at `Router.compile()` time).
2. `BardApp` matches the route and dispatches through app-level and router-level middleware.
3. Handler runs with extractor and DI injection; request-scoped resources are cleaned up via `AsyncExitStack`.
4. Response normalization renders common return types (including streaming).

## Add a Route

```python
import uvicorn

from bard import BardApp, Router


async def health():
    return {"ok": True}


router = Router()
router.get("/health", health)
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

## Add a New Extractor

This is an internal change. Update `bard/extractors.py` and `bard/handler.py`,
then add tests under `tests/`. Use existing extractors as templates and
run `uv run pytest` to verify.

## Form and File Notes

- URL-encoded and multipart are parsed in `bard/form.py`.
- `Form` injects fields; `File` injects uploads.
- `FormData` exposes raw `fields` and `files`.

## Error Rules

- Missing required input -> 422
- Form parsing errors -> 400
- Unexpected errors -> 500

## Quality Checklist

- Add tests for new APIs.
- Keep examples in sync with `README.md`.
- Update `docs/reference/` pages for public changes (start at `docs/reference/index.md`).
