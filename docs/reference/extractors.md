# Extractors

Extractors are declared via `typing.Annotated`:

- `Annotated[T, Json]`
- `Annotated[T, Path(name?)]`
- `Annotated[T, Query(name?)]`
- `Annotated[T, Header(name?)]`
- `Annotated[T, State(name?)]`
- `Annotated[T, Form(name?)]`
- `Annotated[T, File(name?)]`

If the extractor name is omitted (for example `Query`), the parameter name is used as the source key.

`Request` and `WebSocket` can be injected directly as escape hatches.

## Common error rules

- Missing required value -> `HTTPError(422, {"detail": "Missing required value for <name>"})`
  - Defaults are honored (`param: T = default`).
  - Optional types are honored (`T | None` / `Optional[T]` => `None`).
- Type conversion failures -> `HTTPError(422, {"detail": "Invalid <source> <key>"})`

## `Json`

`Annotated[T, Json]` parses `Request.body()` as JSON into type `T`.

- Empty body behaves like "missing value" (default / optional / 422).
- JSON decoding uses `msgspec` (and maps `pydantic.ValidationError` to 422 when applicable).
- Decode/validation errors -> 422 with detail `Invalid JSON for <name>`.

## `Query`

`Annotated[T, Query(name?)]` reads from `Request.query_params[name]`.

- If `T` is `list[U]`, all repeated values are passed as a list.
- Otherwise the first value is used.

## `Path`

`Annotated[T, Path(name?)]` reads from the route path parameters (`/users/{user_id}`).

## `Header`

`Annotated[T, Header(name?)]` reads from `Request.headers[name.lower()]`.

Notes:

- Header lookups are case-insensitive.
- Header keys are decoded as latin-1 and lowercased.

## `State`

`Annotated[T, State(name?)]` reads from `request.state[name]` (the `BardApp.state` dict).

## `Form`

`Annotated[T, Form(name?)]` reads from parsed form fields.

- Invalid form payloads -> `HTTPError(400, "Invalid form data")`.
- `Annotated[FormData, Form]` (no explicit name) injects the full parsed form.
- `Annotated[dict, Form]` (no explicit name) injects a flattened mapping of fields:
  - singletons become `str`
  - repeated fields become `list[str]`

## `File`

`Annotated[T, File(name?)]` reads uploaded files from multipart form data.

Target type behavior:

- `UploadFile` -> injects the file object
- `bytes` -> injects `UploadFile.content`
- `str` -> injects `UploadFile.text()`
- `list[...]` -> injects a list of coerced items for repeated file fields

