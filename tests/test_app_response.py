from __future__ import annotations

import asyncio

from bard import BardApp, HTTPError, Response, Router, StreamingResponse, TestClient


def test_response_variants():
    async def json_response():
        return {"ok": True}

    async def bytes_response():
        return b"bytes"

    async def text_response():
        return "hello"

    async def none_response():
        return None

    async def tuple_response():
        return {"ok": True}, 201, {"x-test": "1"}

    router = Router()
    router.get("/json", json_response)
    router.get("/bytes", bytes_response)
    router.get("/text", text_response)
    router.get("/none", none_response)
    router.get("/tuple", tuple_response)
    app = BardApp(router)

    with TestClient(app) as client:
        json_resp = client.get("/json")
        bytes_resp = client.get("/bytes")
        text_resp = client.get("/text")
        none_resp = client.get("/none")
        tuple_resp = client.get("/tuple")

    assert json_resp.headers["content-type"].startswith("application/json")
    assert json_resp.json()["ok"] is True
    assert bytes_resp.body == b"bytes"
    assert bytes_resp.headers["content-type"].startswith("application/octet-stream")
    assert text_resp.body == b"hello"
    assert none_resp.status == 204
    assert tuple_resp.status == 201
    assert tuple_resp.headers["x-test"] == "1"


def test_response_tuple_status_only():
    async def accepted():
        return "ok", 202

    router = Router()
    router.get("/accepted", accepted)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/accepted")

    assert resp.status == 202
    assert resp.body == b"ok"


def test_response_custom_content_type_preserved():
    async def custom():
        return Response(b"data", headers={"content-type": "application/custom"})

    router = Router()
    router.get("/custom", custom)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/custom")

    assert resp.headers["content-type"] == "application/custom"


def test_response_headers_bytes_roundtrip():
    async def custom():
        return Response(b"data", headers=[(b"x-test", b"1")])

    router = Router()
    router.get("/custom", custom)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/custom")

    assert resp.headers["x-test"] == "1"


def test_response_headers_string_pairs():
    async def custom():
        return Response(b"data", headers=[("x-test", "1")])

    router = Router()
    router.get("/custom", custom)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/custom")

    assert resp.headers["x-test"] == "1"


def test_method_not_found_returns_404():
    async def root():
        return "ok"

    router = Router()
    router.get("/", root)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.post("/")

    assert resp.status == 404


def test_http_error_propagates_status_and_headers():
    async def fail():
        raise HTTPError(400, "bad request", headers={"x-error": "1"})

    router = Router()
    router.get("/fail", fail)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/fail")

    assert resp.status == 400
    assert resp.headers["x-error"] == "1"
    assert resp.json()["detail"] == "bad request"


def test_internal_error_returns_500():
    async def fail():
        raise RuntimeError("boom")

    router = Router()
    router.get("/fail", fail)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/fail")

    assert resp.status == 500
    assert resp.json()["detail"] == "Internal Server Error"


def test_invalid_response_tuple_returns_500():
    async def invalid_tuple():
        return ("a", 1, 2, 3)

    router = Router()
    router.get("/tuple", invalid_tuple)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/tuple")

    assert resp.status == 500
    assert resp.json()["detail"] == "Internal Server Error"


def test_websocket_scope_closes():
    router = Router()
    app = BardApp(router)

    async def run_ws():
        messages = []

        async def receive():
            return {"type": "websocket.connect"}

        async def send(message):
            messages.append(message)

        scope = {"type": "websocket", "asgi": {"version": "3.0"}}
        await app(scope, receive, send)
        return messages

    sent = asyncio.run(run_ws())

    assert sent[0]["type"] == "websocket.close"


def test_websocket_scope_ignores_non_connect():
    router = Router()
    app = BardApp(router)

    async def run_ws():
        messages = []

        async def receive():
            return {"type": "websocket.receive"}

        async def send(message):
            messages.append(message)

        scope = {"type": "websocket", "asgi": {"version": "3.0"}}
        await app(scope, receive, send)
        return messages

    sent = asyncio.run(run_ws())

    assert sent == []


def test_streaming_response_sends_multiple_body_messages():
    async def gen():
        yield b"a"
        yield b"b"

    async def stream():
        return StreamingResponse(gen(), media_type="application/octet-stream")

    router = Router()
    router.get("/stream", stream)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/stream")

    assert resp.body == b"ab"
