from __future__ import annotations

import asyncio

import uvicorn

from bard import BardApp, Router, StreamingResponse


async def chunks():
    for i in range(3):
        yield f"chunk-{i}\n"
        await asyncio.sleep(0.2)


async def stream():
    return StreamingResponse(chunks(), media_type="text/plain; charset=utf-8")


router = Router()
router.get("/stream", stream)
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

