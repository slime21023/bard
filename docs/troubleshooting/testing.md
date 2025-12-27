# Testing

## "TestClient cannot run inside an active event loop"

`TestClient` creates and owns an event loop when used as a context manager, and it refuses to run when a loop is
already running (for example inside `pytest-asyncio` tests).

Options:

- Use `TestClient` in normal (non-async) tests.
- If you need async tests, run a real ASGI server in a separate process/thread and test over HTTP/WebSocket.

## Lifespan not running

Checklist:

- Use `with TestClient(app) as client:` to trigger `app.startup()` and `app.shutdown()`.
- If you call `client.request(...)` without entering the context manager, the request still runs in-process, but
  lifespan will not run unless you call `await app.startup()` / `await app.shutdown()` yourself.

## JSON vs body confusion

`client.request(..., json=..., body=...)` does not allow both. Provide one:

- `json=...` automatically sets `content-type: application/json`
- `body=b"..."` sends raw bytes (set `content-type` yourself if needed)

