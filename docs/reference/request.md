# Request

## `Request`

`Request(scope, receive, state, exit_stack=None)` is injected into HTTP handlers and can also be used as an escape hatch
when extractors are not enough.

## Attributes

- `request.scope`: raw ASGI scope (dict).
- `request.state`: the app-global `dict` from `BardApp.state`.
- `request.exit_stack`: per-request `AsyncExitStack` used for DI cleanup.
- `request.di_cache`: per-request cache for DI providers (`use_cache=True`).

## Properties

- `request.method`: HTTP method (string).
- `request.path`: request path (string).
- `request.headers`: lowercased header mapping (`dict[str, str]`); decoded as latin-1.
- `request.query_params`: parsed query string (`dict[str, list[str]]`), using `parse_qs(..., keep_blank_values=True)`.

## Body

### `await request.body() -> bytes`

- Buffers the full request body in memory.
- Caches the body after the first read.
- Subsequent calls return the cached bytes.

## Forms

### `await request.form() -> FormData`

- Parses form content based on the `content-type` header.
- If no `content-type` is present, returns an empty `FormData`.
- Parses eagerly and keeps uploads in memory (see `UploadFile.content`).
- Caches the parsed form after the first call.

Errors:

- Invalid form payloads raise `HTTPError(400, "Invalid form data")` when used via `Form`/`File` extractors.

