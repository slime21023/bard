from __future__ import annotations

from typing import Annotated

import msgspec
import uvicorn

from bard import BardApp, Json, Router


class CreateUser(msgspec.Struct):
    username: str
    email: str


async def root():
    return "Hello from Bard!"


async def create_user(payload: Annotated[CreateUser, Json]):
    return {
        "status": "success",
        "user": payload.username,
        "email": payload.email,
    }, 201


router = Router()
router.get("/", root)
router.post("/users", create_user)

app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
