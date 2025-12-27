# Responses

## `Response`

`Response(body: bytes, status=200, headers=None, media_type="text/plain; charset=utf-8")`

Notes:

- `headers` may be a `dict[str, str]` or a `list[tuple[bytes, bytes]]`.
- Header keys/values are encoded as latin-1 when a dict is provided.
- If `media_type` is not `None` and no `content-type` header is present, Bard adds one.

## `StreamingResponse`

`StreamingResponse(chunks, status=200, headers=None, media_type="application/octet-stream")`

`chunks` may be `Iterable[bytes|str]` or `AsyncIterable[bytes|str]`.

Notes:

- `str` chunks are encoded as UTF-8 bytes.
- Bard sends one `http.response.body` event per chunk and finishes with an empty final body.

## Return value normalization

Handlers may return:

- `dict` / `list` -> JSON
- `str` -> text
- `bytes` -> binary
- `None` -> 204
- `(body, status)` / `(body, status, headers)`
- `StreamingResponse` or an async iterable of `bytes|str`

Headers:

- `(body, status, headers)` uses the provided headers and still applies the default `content-type` for the chosen body
  kind (unless you include your own `content-type`).
