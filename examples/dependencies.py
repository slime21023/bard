from __future__ import annotations

from contextlib import contextmanager

import uvicorn

from bard import BardApp, Router


class Database:
    def __init__(self) -> None:
        self._open = True

    def ping(self) -> str:
        return "pong" if self._open else "closed"

    def close(self) -> None:
        self._open = False


@contextmanager
def provide_db() -> Database:
    db = Database()
    try:
        yield db
    finally:
        db.close()


async def health(db: Database):
    return {"db": db.ping()}


router = Router()
router.provide(Database, provide_db)
router.get("/health", health)
app = BardApp(router)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

