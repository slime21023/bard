# Routing & Subrouters

## Register Routes

```python
from bard import Router


async def root():
    return {"ok": True}


router = Router()
router.get("/", root)
```

Path parameters use `{name}`:

```python
from typing import Annotated

from bard import Path, Router


async def get_user(user_id: Annotated[int, Path]):
    return {"user_id": user_id}


router = Router()
router.get("/users/{user_id}", get_user)
```

## Subrouters (`include_router`)

Mount a child router under a prefix:

```python
from bard import Router


async def ping():
    return {"ok": True}


child = Router()
child.get("/ping", ping)

parent = Router()
parent.include_router(child, prefix="/api")
```

Resulting route: `GET /api/ping`.

## Router-level Middleware

Router-level middleware applies to routes registered on that router (including routes brought in via `include_router`).

```python
from bard import Request, Router


async def add_header(request: Request, call_next):
    result = await call_next()
    return result, 200, {"x-scope": "child"}


child = Router()
child.add_middleware(add_header)
```

## See Also

- [Advanced routing details](../advanced/routing.md)
