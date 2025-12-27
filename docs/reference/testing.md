# Testing

## `TestClient`

`TestClient(app)` runs the app in-process and triggers lifespan by default.

### Context manager behavior

- `with TestClient(app) as client:` creates a new event loop, runs `app.startup()`, and later runs `app.shutdown()`.
- It cannot run inside an already-running event loop (raises `RuntimeError`).

### Request API

- `client.request(method, path, headers=None, json=None, body=None) -> TestResponse`
  - Provide `json` *or* `body` (not both).
  - `path` may include a query string (e.g. `"/search?page=1"`).
- Convenience methods: `client.get/post/put/delete(...)`.

`TestResponse` fields:

- `status`: HTTP status code
- `headers`: response headers as `dict[str, str]`
- `body`: raw bytes
- `json()`: decode JSON response body

Notes:

- It cannot run inside an already-running event loop.
- Use `TestClient` for unit/in-process tests; use a real ASGI server for integration tests.
