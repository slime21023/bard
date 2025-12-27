from __future__ import annotations

import uvicorn

from bard import BardApp, Request, Router


async def child_root():
    return {"child": True}


async def parent_root():
    return {"parent": True}


async def child_header(request: Request, call_next):
    result = await call_next()
    return result, 200, {"x-scope": "child"}


child = Router()
child.add_middleware(child_header)
child.get("/", child_root)

parent = Router()
parent.get("/", parent_root)
parent.include_router(child, prefix="/api")

app = BardApp(parent)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

