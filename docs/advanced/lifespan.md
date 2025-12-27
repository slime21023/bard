# Lifespan & Resources

## Lifespan

Use an `asynccontextmanager` to initialize and tear down resources:

```python
from contextlib import asynccontextmanager

from bard import BardApp, Router


@asynccontextmanager
async def lifespan(app):
    app.state["db"] = "ready"
    yield
    app.state["db"] = "closed"


router = Router()
app = BardApp(router, lifespan=lifespan)
```

## DI Cleanup

Request-scoped DI resources are cleaned up automatically using `AsyncExitStack` (LIFO), even on errors.

