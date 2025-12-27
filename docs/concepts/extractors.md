# Extractors

Use `typing.Annotated` to declare where inputs come from.

```python
from typing import Annotated

from bard import Header, Json, Path, Query, Router, State


async def search(
    q: Annotated[str, Query],
    agent: Annotated[str, Header("user-agent")],
    user_id: Annotated[int, Path],
    db: Annotated[str, State("db")],
):
    return {"q": q, "agent": agent, "user_id": user_id, "db": db}


router = Router()
router.get("/users/{user_id}", search)
```

## Forms & Files

```python
from typing import Annotated

from bard import File, Form, FormData, Router, UploadFile


async def submit(name: Annotated[str, Form]):
    return {"name": name}


async def upload(file: Annotated[UploadFile, File("file")]):
    return {"filename": file.filename, "size": len(file.content)}


async def capture(form: Annotated[FormData, Form]):
    return {"fields": form.fields, "files": list(form.files)}


router = Router()
router.post("/submit", submit)
router.post("/upload", upload)
router.post("/capture", capture)
```

## Error Rules

- Missing required value -> 422
- Type conversion errors -> 422
- Invalid form data -> 400

## See Also

- [Conversion rules](../advanced/conversion.md)
