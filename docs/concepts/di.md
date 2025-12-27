# Dependencies (DI)

## Type-based Providers

Register a provider once, then inject by parameter type.

```python
from contextlib import contextmanager

from bard import Router


class Database:
    def ping(self) -> str:
        return "pong"

    def close(self) -> None:
        pass


@contextmanager
def provide_db():
    db = Database()
    try:
        yield db
    finally:
        db.close()


async def health(db: Database):
    return {"db": db.ping()}


router = Router()
router.provide(Database, provide_db)
router.get("/health", health)
```

Providers may return:

- Plain object `T`
- `contextmanager[T]` / `asynccontextmanager[T]`
- Objects with `close()` / `aclose()`

Request-scoped cleanup runs automatically (LIFO) via `AsyncExitStack`.

## Explicit Overrides (`Depends`)

Use `Depends(...)` to override/parameterize a dependency at the parameter level.

```python
from typing import Annotated

from bard import Depends, Router


class Token:
    def __init__(self, value: str) -> None:
        self.value = value


def provide_token() -> Token:
    return Token("demo")


async def whoami(token: Annotated[Token, Depends(provide_token)]):
    return {"token": token.value}


router = Router()
router.get("/whoami", whoami)
```

## See Also

- [Lifespan and cleanup boundaries](../advanced/lifespan.md)
