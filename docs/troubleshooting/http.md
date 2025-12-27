# HTTP 400 / 422 / 500

## 400: invalid form data

You will typically see this when using `Form` / `File` extractors and the request body cannot be parsed as form data.

Checklist:

- Send the correct `content-type`:
  - `application/x-www-form-urlencoded`
  - `multipart/form-data; boundary=...`
- Avoid mixing JSON and form parsing for the same request.
- Remember: request bodies are buffered in memory; very large uploads can hit memory limits.

## 422: missing required value

The most common 422 payload is:

- `{"detail": "Missing required value for <param>"}`.

Causes:

- A required extractor value was missing (query/header/path/form/file/json body).
- The handler parameter was not optional and had no Python default.

Fixes:

- Provide a default: `limit: int = 50`
- Make it optional: `limit: int | None = None`
- Ensure the request includes the required key (`?limit=...`, header, `{path_param}`, etc.)

## 422: conversion failures

Typical examples:

- `Invalid query parameter <key>`
- `Invalid path parameter <key>`
- `Invalid header <key>`
- `Invalid form field <key>`
- `Invalid JSON for <param>`

Checklist:

- Confirm the declared target type matches the payload (`int` vs `"abc"`, `list[int]` vs single value, etc.).
- For headers, remember that keys are case-insensitive and normalized to lowercase.
- For JSON, empty body behaves like "missing" (default / optional / 422).

## 500: internal server error

500 means an unhandled exception escaped the handler/middleware (or an exception handler raised).

Checklist:

- Add an exception handler to surface details during development:

```python
from bard import BardApp, Request, Router

def handle_exc(request: Request, exc: BaseException):
    return {"detail": str(exc)}, 500

router = Router()
app = BardApp(router)
app.add_exception_handler(Exception, handle_exc)
```

- Verify your middleware calls `await call_next()` unless you intentionally short-circuit the request.
- If you are streaming (`StreamingResponse`), remember that DI cleanup happens after the stream finishes or is cancelled.

