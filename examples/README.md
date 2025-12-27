# Examples

Run examples with uv from the repo root:

```bash
uv run python examples/quickstart.py
```

## Quickstart

Basic routes and JSON extraction.

Try it:

```bash
curl http://127.0.0.1:8000/
curl -X POST http://127.0.0.1:8000/users \
  -H "content-type: application/json" \
  -d "{\"username\":\"demo\",\"email\":\"demo@example.com\"}"
```

## Forms & Files

Form fields and file uploads.

Run:

```bash
uv run python examples/forms_files.py
```

Try it:

```bash
curl -X POST http://127.0.0.1:8000/submit \
  -H "content-type: application/x-www-form-urlencoded" \
  -d "name=bard"

curl -X POST http://127.0.0.1:8000/upload \
  -F "file=@README.md"
```

## Dependencies (DI)

Type-based providers with request-scoped cleanup.

Run:

```bash
uv run python examples/dependencies.py
```

Try it:

```bash
curl http://127.0.0.1:8000/health
```

## Middleware

App-level middleware adding response headers.

Run:

```bash
uv run python examples/middleware.py
```

Try it:

```bash
curl -i http://127.0.0.1:8000/
```

## Subrouter (include_router)

Mount a child router under a prefix (with router-level middleware).

Run:

```bash
uv run python examples/subrouter.py
```

Try it:

```bash
curl -i http://127.0.0.1:8000/
curl -i http://127.0.0.1:8000/api
```

## Streaming

Streaming response using an async generator.

Run:

```bash
uv run python examples/streaming.py
```

Try it:

```bash
curl http://127.0.0.1:8000/stream
```

## WebSocket

WebSocket endpoint that sends one message then closes.

Run:

```bash
uv run python examples/websocket.py
```
