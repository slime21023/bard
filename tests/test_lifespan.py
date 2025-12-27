from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

from bard import BardApp, Router, State, TestClient


def test_lifespan_sets_state():
    @asynccontextmanager
    async def lifespan(app):
        app.state["db"] = "ready"
        yield
        app.state["db"] = "closed"

    async def read_state(db: Annotated[str, State("db")]):
        return {"db": db}

    router = Router()
    router.get("/", read_state)
    app = BardApp(router, lifespan=lifespan)

    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.json()["db"] == "ready"

    assert app.state["db"] == "closed"


def test_lifespan_scope_ignores_non_startup():
    router = Router()
    app = BardApp(router)
    messages = []

    async def receive():
        return {"type": "lifespan.shutdown"}

    async def send(message):
        messages.append(message)

    scope = {"type": "lifespan", "asgi": {"version": "3.0"}}
    asyncio.run(app(scope, receive, send))

    assert messages == []


def test_lifespan_scope_without_lifespan():
    router = Router()
    app = BardApp(router)
    messages = []
    queue = [
        {"type": "lifespan.startup"},
        {"type": "lifespan.shutdown"},
    ]

    async def receive():
        return queue.pop(0)

    async def send(message):
        messages.append(message)

    scope = {"type": "lifespan", "asgi": {"version": "3.0"}}
    asyncio.run(app(scope, receive, send))

    assert messages == [
        {"type": "lifespan.startup.complete"},
        {"type": "lifespan.shutdown.complete"},
    ]


def test_lifespan_startup_failure():
    @asynccontextmanager
    async def lifespan(app):
        raise RuntimeError("boom")
        yield

    router = Router()
    app = BardApp(router, lifespan=lifespan)
    messages = []

    async def receive():
        return {"type": "lifespan.startup"}

    async def send(message):
        messages.append(message)

    scope = {"type": "lifespan", "asgi": {"version": "3.0"}}
    asyncio.run(app(scope, receive, send))

    assert messages[0]["type"] == "lifespan.startup.failed"


def test_lifespan_shutdown_failure():
    class FailingLifespan:
        async def __aenter__(self):
            return None

        async def __aexit__(self, exc_type, exc, tb):
            raise RuntimeError("shutdown boom")

    def lifespan(app):
        return FailingLifespan()

    router = Router()
    app = BardApp(router, lifespan=lifespan)
    messages = []
    queue = [
        {"type": "lifespan.startup"},
        {"type": "lifespan.shutdown"},
    ]

    async def receive():
        return queue.pop(0)

    async def send(message):
        messages.append(message)

    scope = {"type": "lifespan", "asgi": {"version": "3.0"}}
    asyncio.run(app(scope, receive, send))

    assert messages[0]["type"] == "lifespan.startup.complete"
    assert messages[1]["type"] == "lifespan.shutdown.failed"


def test_lifespan_shutdown_message_missing():
    @asynccontextmanager
    async def lifespan(app):
        yield

    router = Router()
    app = BardApp(router, lifespan=lifespan)
    messages = []
    queue = [
        {"type": "lifespan.startup"},
        {"type": "lifespan.ping"},
    ]

    async def receive():
        return queue.pop(0)

    async def send(message):
        messages.append(message)

    scope = {"type": "lifespan", "asgi": {"version": "3.0"}}
    asyncio.run(app(scope, receive, send))

    assert messages == [{"type": "lifespan.startup.complete"}]
