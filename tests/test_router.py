from __future__ import annotations

from typing import Annotated

import pytest

from bard import BardApp, Path, Router, TestClient


def test_head_falls_back_to_get():
    async def root():
        return "ok"

    router = Router()
    router.get("/", root)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.request("HEAD", "/")

    assert resp.status == 200


def test_router_static_over_param():
    async def me():
        return {"user": "me"}

    async def user(user_id: Annotated[str, Path]):
        return {"user": user_id}

    router = Router()
    router.get("/users/me", me)
    router.get("/users/{user_id}", user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/users/me")

    assert resp.json()["user"] == "me"


def test_router_duplicate_route_raises():
    async def root():
        return "ok"

    router = Router()
    router.get("/", root)

    with pytest.raises(ValueError):
        router.get("/", root)


def test_router_path_must_start_with_slash():
    async def root():
        return "ok"

    router = Router()

    with pytest.raises(ValueError):
        router.get("missing-slash", root)


def test_router_add_after_app_init():
    async def later():
        return {"ok": True}

    router = Router()
    app = BardApp(router)
    router.get("/later", later)

    with TestClient(app) as client:
        resp = client.get("/later")

    assert resp.json()["ok"] is True


def test_router_put_delete_routes():
    async def update():
        return {"ok": True}

    async def remove():
        return {"ok": True}

    router = Router()
    router.put("/items", update)
    router.delete("/items", remove)
    app = BardApp(router)

    with TestClient(app) as client:
        put_resp = client.put("/items")
        delete_resp = client.delete("/items")

    assert put_resp.json()["ok"] is True
    assert delete_resp.json()["ok"] is True


def test_router_param_names_bound_per_method():
    async def get_user(user_id: Annotated[str, Path]):
        return {"user_id": user_id}

    async def post_user(id: Annotated[str, Path]):
        return {"id": id}

    router = Router()
    router.get("/users/{user_id}", get_user)
    router.post("/users/{id}", post_user)
    app = BardApp(router)

    with TestClient(app) as client:
        get_resp = client.get("/users/alpha")
        post_resp = client.post("/users/bravo")

    assert get_resp.json()["user_id"] == "alpha"
    assert post_resp.json()["id"] == "bravo"


def test_head_param_uses_get_param_name():
    async def get_user(user_id: Annotated[str, Path]):
        return {"user_id": user_id}

    router = Router()
    router.get("/users/{user_id}", get_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.request("HEAD", "/users/alpha")

    assert resp.json()["user_id"] == "alpha"


def test_router_double_slash_matches():
    async def root():
        return {"ok": True}

    router = Router()
    router.get("/double/slash", root)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/double//slash")

    assert resp.json()["ok"] is True


def test_router_root_path():
    async def root():
        return {"ok": True}

    router = Router()
    router.get("/", root)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/")

    assert resp.json()["ok"] is True


def test_route_trailing_slash_matches():
    async def root():
        return "ok"

    router = Router()
    router.get("/trailing", root)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/trailing/")

    assert resp.status == 200


def test_router_unmatched_path_returns_404():
    async def root():
        return "ok"

    router = Router()
    router.get("/known", root)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/unknown")

    assert resp.status == 404


def test_get_callsite_locals_no_frame(monkeypatch):
    import bard.router as router_module

    monkeypatch.setattr(router_module.inspect, "currentframe", lambda: None)

    async def root():
        return "ok"

    router = Router()
    router.get("/", root)


def test_router_multiple_params():
    async def show(
        user_id: Annotated[int, Path],
        post_id: Annotated[str, Path],
    ):
        return {"user_id": user_id, "post_id": post_id}

    router = Router()
    router.get("/users/{user_id}/posts/{post_id}", show)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/users/42/posts/abc")

    assert resp.json()["user_id"] == 42
    assert resp.json()["post_id"] == "abc"


def test_include_router_prefix_routes():
    async def child_handler():
        return {"ok": True}

    child = Router()
    child.get("/ping", child_handler)

    parent = Router()
    parent.include_router(child, prefix="/api")
    app = BardApp(parent)

    with TestClient(app) as client:
        resp = client.get("/api/ping")

    assert resp.json()["ok"] is True


def test_include_router_prefix_root_path():
    async def child_root():
        return {"root": True}

    child = Router()
    child.get("/", child_root)

    parent = Router()
    parent.include_router(child, prefix="/api")
    app = BardApp(parent)

    with TestClient(app) as client:
        resp1 = client.get("/api")
        resp2 = client.get("/api/")

    assert resp1.json()["root"] is True
    assert resp2.json()["root"] is True
