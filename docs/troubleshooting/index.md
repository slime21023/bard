# Troubleshooting

This section focuses on diagnosis: how to quickly tell whether an error is caused by extractors, conversion, DI,
middleware, or handler logic.

## Quick pointers

- If you see `422` with `{"detail": ...}`, it is usually an extractor/conversion problem.
- If the app fails to start with `MissingProviderError` / `TypeError("Missing extractor ...")`, it is a handler/DI
  compilation problem (often caused by provider registration order).
- If you see `RuntimeError("TestClient cannot run inside an active event loop")`, it is a test harness issue.

## Pages

- [HTTP 400/422/500](http.md)
- [DI & Providers](di.md)
- [WebSocket](websocket.md)
- [Testing](testing.md)

