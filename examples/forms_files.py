from __future__ import annotations

from typing import Annotated

import uvicorn

from bard import BardApp, File, Form, FormData, Router, UploadFile


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

app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
