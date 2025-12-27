from __future__ import annotations

import asyncio

from bard import BardApp, Request, Router, TestClient


def test_request_injection():
    async def show_path(request: Request):
        return {"path": request.path}

    router = Router()
    router.get("/ping", show_path)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/ping")

    assert resp.json()["path"] == "/ping"


def test_request_headers_are_lowercase():
    async def read_headers(request: Request):
        return {"agent": request.headers.get("user-agent")}

    router = Router()
    router.get("/headers", read_headers)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/headers", headers={"User-Agent": "Probe"})

    assert resp.json()["agent"] == "Probe"


def test_request_body_cached():
    async def read_body(request: Request):
        body_first = await request.body()
        body_second = await request.body()
        return {"same": body_first == body_second, "body": body_first.decode("utf-8")}

    router = Router()
    router.post("/body", read_body)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.request("POST", "/body", body=b"hello")

    assert resp.json()["same"] is True
    assert resp.json()["body"] == "hello"


def test_request_query_params_list():
    async def read_query(request: Request):
        return {"tags": request.query_params.get("tag")}

    router = Router()
    router.get("/query", read_query)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/query?tag=a&tag=b")

    assert resp.json()["tags"] == ["a", "b"]


def test_request_headers_duplicate_last_wins():
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        scope={
            "type": "http",
            "headers": [(b"x-token", b"first"), (b"x-token", b"second")],
            "query_string": b"",
        },
        receive=receive,
        state={},
    )

    assert request.headers["x-token"] == "second"


def test_request_method_property():
    request = Request(
        scope={"type": "http", "method": "POST", "headers": [], "query_string": b""},
        receive=lambda: None,
        state={},
    )

    assert request.method == "POST"


def test_request_body_skips_non_request_messages():
    messages = [
        {"type": "http.response"},
        {"type": "http.request", "body": b"hello", "more_body": False},
    ]

    async def receive():
        return messages.pop(0)

    request = Request(
        scope={"type": "http", "headers": [], "query_string": b""},
        receive=receive,
        state={},
    )

    body = asyncio.run(request.body())

    assert body == b"hello"


def test_request_body_disconnect_returns_partial():
    async def receive_disconnect():
        return {"type": "http.disconnect"}

    request = Request(
        scope={"type": "http", "headers": [], "query_string": b""},
        receive=receive_disconnect,
        state={},
    )

    body = asyncio.run(request.body())

    assert body == b""
