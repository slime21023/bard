from __future__ import annotations

import uvicorn

from bard import BardApp, Router, WebSocket


async def ws_handler(ws: WebSocket):
    await ws.send_text("hello")
    await ws.close()


router = Router()
router.websocket("/ws", ws_handler)
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

