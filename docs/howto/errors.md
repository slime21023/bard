# Error Handling

## `HTTPError`

Raise `HTTPError` to return an explicit status code and optional headers.

```python
from bard import HTTPError


async def validate():
    raise HTTPError(400, "invalid input", headers={"x-error": "1"})
```

## Custom Exception Handlers

Override default 500 responses:

```python
from bard import BardApp, Request, Router


async def fail():
    raise RuntimeError("boom")


def handle_runtime_error(request: Request, exc: BaseException):
    return {"detail": str(exc)}, 418


router = Router()
router.get("/fail", fail)
app = BardApp(router)
app.add_exception_handler(RuntimeError, handle_runtime_error)
```

