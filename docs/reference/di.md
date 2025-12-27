# Dependencies (DI)

## Type-based providers

- `router.provide(Type, provider, use_cache=True)`
- `app.provide(Type, provider, use_cache=True)`

Handlers can then request `dep: Type` without an extractor.

### Provider call style

Providers are compiled the same way as handlers, so a provider can be sync or async and can itself declare
dependencies via extractors/DI.

```python
from typing import Annotated

from bard import Header, Router


class Token:
    def __init__(self, value: str) -> None:
        self.value = value


async def provide_token(authorization: Annotated[str, Header("authorization")]) -> Token:
    return Token(authorization.removeprefix("Bearer ").strip())


router = Router()
router.provide(Token, provide_token)
```

### Caching and scope

- With `use_cache=True` (default), the resolved value is cached in `request.di_cache` for the duration of the request
  (or WebSocket connection).
- With `use_cache=False`, the provider is called each time the dependency is requested.

## `Depends`

`Depends(provider, use_cache=True)` overrides DI at the parameter level:

```python
from typing import Annotated

from bard import Depends

async def handler(dep: Annotated[object, Depends(lambda: object())]):
    ...
```

Notes:

- The cache key for `Depends` is based on the provider function identity (not the annotated type).
- `Depends` is checked before type-based DI.

## Cleanup

Providers may return:

- Plain object `T`
- `contextmanager[T]` / `asynccontextmanager[T]`
- Objects with `close()` / `aclose()`

Request/connection scoped cleanup runs automatically (LIFO).

Cleanup is tied to the per-request/connection `AsyncExitStack` (`Request.exit_stack` / `WebSocket.exit_stack`).

## Missing provider vs missing extractor

If a parameter has no extractor metadata and is not wrapped in `Depends(...)`, Bard attempts type-based DI:

- If there is no provider for the requested type:
  - "Request-like" data types (`str`, `int`, `list[...]`, `dict[...]`, unions, etc.) are treated as missing extractors
    and fail compilation with `TypeError("Missing extractor for <name>")`.
  - Other types fail compilation with `MissingProviderError(...)`.

