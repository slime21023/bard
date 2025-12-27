from __future__ import annotations

from bard import BardApp, Request, Router, TestClient


def test_router_level_middleware_applies_only_to_included_routes():
    async def child_handler():
        return {"ok": True}

    async def parent_handler():
        return {"ok": True}

    async def child_mw(request: Request, call_next):
        result = await call_next()
        return result, 200, {"x-child": "1"}

    child = Router()
    child.add_middleware(child_mw)
    child.get("/ping", child_handler)

    parent = Router()
    parent.get("/root", parent_handler)
    parent.include_router(child, prefix="/api")
    app = BardApp(parent)

    with TestClient(app) as client:
        child_resp = client.get("/api/ping")
        parent_resp = client.get("/root")

    assert child_resp.headers["x-child"] == "1"
    assert "x-child" not in parent_resp.headers


def test_app_level_and_router_level_middleware_order():
    async def handler(request: Request):
        return {"order": request.di_cache["order"]}

    async def app_mw(request: Request, call_next):
        request.di_cache.setdefault("order", []).append("app-before")
        result = await call_next()
        request.di_cache["order"].append("app-after")
        return result

    async def router_mw(request: Request, call_next):
        request.di_cache.setdefault("order", []).append("router-before")
        result = await call_next()
        request.di_cache["order"].append("router-after")
        return result

    child = Router()
    child.add_middleware(router_mw)
    child.get("/ping", handler)

    parent = Router()
    parent.include_router(child, prefix="/api")
    app = BardApp(parent)
    app.add_middleware(app_mw)

    with TestClient(app) as client:
        resp = client.get("/api/ping")

    assert resp.json()["order"] == ["app-before", "router-before", "router-after", "app-after"]

