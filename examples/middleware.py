from __future__ import annotations

import time

import uvicorn

from bard import BardApp, Request, Router


async def root():
    return {"ok": True}


async def timing_middleware(request: Request, call_next):
    started = time.perf_counter()
    result = await call_next()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return result, 200, {"x-elapsed-ms": f"{elapsed_ms:.2f}"}


async def error_envelope(request: Request, call_next):
    try:
        return await call_next()
    except Exception as exc:
        return {"detail": str(exc)}, 500


router = Router()
router.get("/", root)
app = BardApp(router)

app.add_middleware(error_envelope)
app.add_middleware(timing_middleware)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

