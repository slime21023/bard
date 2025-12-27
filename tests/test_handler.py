from __future__ import annotations

from typing import Annotated

import pytest

from bard import BardApp, Json, Path, Query, Router, TestClient
from bard.extractors import _Extractor


def test_sync_handler_returns_value():
    def root():
        return {"ok": True}

    router = Router()
    router.get("/", root)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/")

    assert resp.json()["ok"] is True


def test_compile_handler_unsupported_param_kind():
    async def handler(*values: int):
        return {"values": values}

    router = Router()

    with pytest.raises(TypeError):
        router.get("/", handler)


def test_compile_handler_missing_annotation():
    async def handler(value):
        return {"value": value}

    router = Router()

    with pytest.raises(TypeError):
        router.get("/", handler)


def test_compile_handler_missing_extractor():
    async def handler(value: int):
        return {"value": value}

    router = Router()

    with pytest.raises(TypeError):
        router.get("/", handler)


def test_compile_handler_unknown_extractor():
    class Custom(_Extractor):
        pass

    async def handler(value: Annotated[int, Custom()]):  # type: ignore[misc]
        return {"value": value}

    router = Router()

    with pytest.raises(TypeError):
        router.get("/", handler)


def test_path_name_mismatch_returns_422():
    async def get_user(user_id: Annotated[int, Path("user_id")]):
        return {"user_id": user_id}

    router = Router()
    router.get("/users/{id}", get_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/users/1")

    assert resp.status == 422
    assert "Missing required value" in resp.json()["detail"]


def test_resolve_type_hints_failure_raises():
    async def handler(payload: "MissingType"):
        return {"payload": payload}

    router = Router()

    with pytest.raises(TypeError):
        router.get("/", handler)


def test_resolve_type_hints_handles_empty_cells():
    if False:
        token = "unused"

    async def handler(value: Annotated[int, Query]):
        return {"value": value, "token": token}  # type: ignore[name-defined]

    router = Router()
    router.get("/", handler)


def test_non_pydantic_json_error_returns_500():
    class Broken:
        @classmethod
        def model_validate_json(cls, value: bytes):
            raise RuntimeError("boom")

    async def create(payload: Annotated[Broken, Json]):
        return {"payload": payload}

    router = Router()
    router.post("/items", create)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.post("/items", json={"ok": True})

    assert resp.status == 500
