from __future__ import annotations

from bard import BardApp, Request, Router, TestClient


def test_http_middleware_wraps_handler_and_preserves_order():
    async def handler(request: Request):
        order = request.di_cache.get("order", [])
        order.append("handler")
        return {"order": order}

    async def mw1(request: Request, call_next):
        request.di_cache.setdefault("order", []).append("mw1-before")
        result = await call_next()
        request.di_cache["order"].append("mw1-after")
        return result

    async def mw2(request: Request, call_next):
        request.di_cache.setdefault("order", []).append("mw2-before")
        result = await call_next()
        request.di_cache["order"].append("mw2-after")
        return result

    router = Router()
    router.get("/", handler)
    app = BardApp(router)
    app.add_middleware(mw1)
    app.add_middleware(mw2)

    with TestClient(app) as client:
        resp = client.get("/")

    assert resp.json()["order"] == ["mw1-before", "mw2-before", "handler", "mw2-after", "mw1-after"]


def test_http_middleware_can_add_headers_via_tuple_response():
    async def handler():
        return {"ok": True}

    async def add_header(request: Request, call_next):
        result = await call_next()
        if isinstance(result, tuple):
            body, status = result
            headers = None
        else:
            body, status, headers = result, 200, {}
        headers = headers or {}
        headers["x-mw"] = "1"
        return body, status, headers

    router = Router()
    router.get("/", handler)
    app = BardApp(router)
    app.add_middleware(add_header)

    with TestClient(app) as client:
        resp = client.get("/")

    assert resp.headers["x-mw"] == "1"
