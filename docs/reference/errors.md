# Errors

## `HTTPError`

Raise `HTTPError(status_code, detail, headers=None)` to return an explicit error response.

Behavior:

- Returned response body is JSON: `{"detail": <detail>}`.
- `headers` are added to the response (and `content-type: application/json` is set).

## Exception handlers

Use `app.add_exception_handler(ExceptionType, handler)` to translate exceptions into a normal return value.

Notes:

- The handler is selected by walking the exception type MRO (most specific first).
- Handlers may be sync or async.
- For HTTP requests, the handler return value is converted using the normal response rules.
- If an exception handler raises, Bard falls back to a 500 response.
