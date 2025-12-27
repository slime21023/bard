# Public API

This page lists the primary symbols intended for import from `bard`.

```python
from bard import (
    BardApp,
    Router,
    Request,
    WebSocket,
    Response,
    StreamingResponse,
    HTTPError,
    Depends,
    Json,
    Query,
    Path,
    Header,
    State,
    Form,
    File,
    FormData,
    UploadFile,
    TestClient,
)
```

## Core

- `BardApp`: ASGI application wrapper around a `Router`.
- `Router`: route registration, matching, and handler compilation.
- `Request`: HTTP request wrapper (headers/query/body/form + DI cache).
- `WebSocket`: WebSocket wrapper (accept/receive/send/close + DI cache).

## Responses

- `Response`: send an explicit raw HTTP response.
- `StreamingResponse`: stream response bodies from iterables / async iterables.

## Errors

- `HTTPError`: raise to return a specific HTTP status and JSON `{"detail": ...}` payload.

## DI

- `Depends`: parameter-level dependency override (provider callable).

## Extractors

Extractors are used via `typing.Annotated[T, Extractor(...)]`.

- `Json`: parse request body as JSON into type `T`.
- `Query(name?)`: read query parameter `name` (defaults to parameter name).
- `Path(name?)`: read path parameter `{name}` (defaults to parameter name).
- `Header(name?)`: read header `name` (defaults to parameter name; case-insensitive).
- `State(name?)`: read `app.state[name]` (defaults to parameter name).
- `Form(name?)`: read form field `name` (defaults to parameter name).
- `File(name?)`: read uploaded file field `name` (defaults to parameter name).

## Forms / Files

- `FormData`: parsed `{fields, files}` container returned by `Request.form()`.
- `UploadFile`: in-memory uploaded file wrapper (used by `File` extractor).

## Testing

- `TestClient`: in-process HTTP client for unit tests (runs lifespan by default).

