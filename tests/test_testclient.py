from __future__ import annotations

import asyncio

import pytest

from bard import BardApp, Router, TestClient


def test_testclient_exit_without_enter():
    async def root():
        return {"ok": True}

    router = Router()
    router.get("/", root)
    app = BardApp(router)
    client = TestClient(app)

    client.__exit__(None, None, None)


def test_testclient_json_and_body_error():
    async def root():
        return {"ok": True}

    router = Router()
    router.get("/", root)
    app = BardApp(router)
    client = TestClient(app)

    with pytest.raises(ValueError):
        client.request("GET", "/", json={"ok": True}, body=b"data")


def test_testclient_without_context_uses_asyncio_run():
    async def root():
        return {"ok": True}

    router = Router()
    router.get("/", root)
    app = BardApp(router)
    client = TestClient(app)

    resp = client.get("/")

    assert resp.json()["ok"] is True


def test_testclient_put_delete_helpers():
    async def put_handler():
        return {"method": "put"}

    async def delete_handler():
        return {"method": "delete"}

    router = Router()
    router.put("/items", put_handler)
    router.delete("/items", delete_handler)
    app = BardApp(router)

    with TestClient(app) as client:
        put_resp = client.put("/items")
        delete_resp = client.delete("/items")

    assert put_resp.json()["method"] == "put"
    assert delete_resp.json()["method"] == "delete"


def test_testclient_active_event_loop_raises():
    async def run():
        async def root():
            return {"ok": True}

        router = Router()
        router.get("/", root)
        app = BardApp(router)

        with pytest.raises(RuntimeError):
            with TestClient(app):
                pass

    asyncio.run(run())


def test_testclient_receive_body_sent_branch():
    async def app(scope, receive, send):
        await receive()
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    client = TestClient(app)

    resp = client.request("POST", "/test", body=b"payload")

    assert resp.body == b"ok"
