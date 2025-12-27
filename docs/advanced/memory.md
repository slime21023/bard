# Memory & Buffering

## Request Bodies

`Request.body()` buffers the whole body in memory and caches it for subsequent reads.

## Forms & Uploads

Form parsing is eager and uploads are kept in memory via `UploadFile.content`.

## Streaming Responses

`StreamingResponse` streams response bodies, but request-scoped resources (DI) are held until the stream finishes or is cancelled.

## Current Limitations

- HTTP request body streaming is not implemented.
- Large uploads should be handled upstream or proxied.

