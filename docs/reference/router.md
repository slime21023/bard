# Router

`Router()` registers routes and compiles handlers based on type hints (extractors + DI providers).

## Register routes

- `router.get/post/put/delete(path, handler)`
- `router.websocket(path, handler)`

Path parameters use `{name}`.

Notes:

- `handler` may be sync or async.
- Only keyword-capable parameters are supported (`POSITIONAL_OR_KEYWORD` / `KEYWORD_ONLY`).
- Each handler parameter must have a type annotation (extractor / DI uses it).
- Duplicate registrations for the same method+path raise `ValueError`.

## Subrouters

- `router.include_router(other, prefix="")`: re-registers all routes from `other` under `prefix`.

`prefix` rules:

- Must be empty or start with `/`.
- Trailing `/` is stripped.
- `prefix="/api"` + child route `"/"` results in `"/api"`.

## DI providers

- `router.provide(Type, provider, use_cache=True)`

Providers are merged when using `include_router`. Conflicts raise `ValueError`.

## Router-level middleware

- `router.add_middleware(middleware)` (HTTP)
- `router.add_websocket_middleware(middleware)` (WebSocket)

Router-level middleware applies only to routes registered on that router (including included routes).

## Matching behavior

- Static segments win over parameter segments (e.g. `/users/me` beats `/users/{user_id}`).
- `HEAD` falls back to `GET` if no explicit `HEAD` handler exists.
- Paths are normalized by splitting on `/` and ignoring empty segments, so repeated and trailing slashes match:
  - `GET /users//me` matches `/users/me`
  - `GET /users/me/` matches `/users/me`

## Compilation timing and missing providers

- `BardApp(router)` calls `router.compile()`, which compiles all registered handlers.
- If a handler (or a provider) requires a DI provider that has not been registered, compilation fails with
  `MissingProviderError` or `TypeError` (for missing extractors).
- When adding routes before the first `compile()`, Bard may defer compilation until `compile()`; register providers
  before creating the app to catch errors early.
