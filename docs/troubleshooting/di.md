# DI & Providers

## "Missing extractor for <name>" (compile-time)

This is raised during handler compilation when a parameter has:

- no extractor metadata (no `Annotated[..., Query/Path/... ]`)
- no `Depends(...)`
- and its type looks like "request data" (`str`, `int`, `list[...]`, `dict[...]`, unions, etc.)

Fix:

- Add an extractor (for example `Annotated[int, Query]`), or
- Add a DI provider and request a non-request-data type (e.g. `Database`), or
- Wrap with `Depends(...)` if you want explicit provider resolution.

## `MissingProviderError` (compile-time)

This means Bard decided the parameter is a dependency type, but no provider was registered.

Most common causes:

- The provider was registered after creating `BardApp(router)` (the app constructor compiles the router).
- A provider depends on another provider that was never registered.

Fixes:

- Register providers before building the app:

```python
from bard import BardApp, Router

router = Router()
router.provide(object, lambda: object())
app = BardApp(router)
```

- If using subrouters, ensure providers are registered on the router being included *before* `include_router(...)`
  (provider conflicts raise `ValueError`).

## Provider cleanup and "leaked" resources

If your provider returns a resource that needs cleanup, Bard can manage it automatically when you return:

- a context manager / async context manager, or
- an object with `close()` / `aclose()`

Checklist:

- Ensure your provider returns the context manager itself (not the entered value) if you expect `__enter__/__exit__`
  to run.
- Remember that streaming responses hold request-scoped resources until the stream completes or is cancelled.

## Caching surprises

With `use_cache=True`, a dependency is computed once per request/connection and reused.

If you need a fresh value each injection:

- set `use_cache=False` in `router.provide(...)`, or
- set `use_cache=False` in `Depends(provider, use_cache=False)`.

