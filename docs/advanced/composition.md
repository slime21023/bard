# Composition

## Route Registration Helpers

Organize larger apps by grouping route registration into helpers:

```python
from bard import Router


def add_health_routes(router: Router) -> None:
    async def health():
        return {"ok": True}

    router.get("/health", health)
```

## Subrouters

Use `Router.include_router()` to group endpoints by prefix.

