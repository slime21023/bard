from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from typing import Annotated

import pytest

from bard import BardApp, Depends, HTTPError, Request, Router, TestClient


def test_type_based_injection_resolves():
    class Database:
        pass

    def provide_db() -> Database:
        return Database()

    async def read(db: Database):
        return {"ok": isinstance(db, Database)}

    router = Router()
    router.provide(Database, provide_db)
    router.get("/db", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/db")

    assert resp.json()["ok"] is True


def test_type_based_injection_request_cache_reuses_value():
    class Database:
        pass

    calls = {"count": 0}

    def provide_db() -> Database:
        calls["count"] += 1
        return Database()

    async def read(db1: Database, db2: Database):
        return {"same": db1 is db2}

    router = Router()
    router.provide(Database, provide_db)
    router.get("/db", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/db")

    assert resp.json()["same"] is True
    assert calls["count"] == 1


def test_depends_override_wins_over_type_provider():
    class Database:
        pass

    type_instance = Database()
    depends_instance = Database()

    def provide_type() -> Database:
        return type_instance

    def provide_depends() -> Database:
        return depends_instance

    async def read(db: Annotated[Database, Depends(provide_depends)]):
        return {"same": db is depends_instance}

    router = Router()
    router.provide(Database, provide_type)
    router.get("/db", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/db")

    assert resp.json()["same"] is True


def test_dependency_contextmanager_cleanup_runs_on_success():
    class Resource:
        pass

    events: list[str] = []

    @contextmanager
    def provide_resource():
        events.append("enter")
        yield Resource()
        events.append("exit")

    async def read(resource: Resource):
        return {"ok": isinstance(resource, Resource)}

    router = Router()
    router.provide(Resource, provide_resource)
    router.get("/r", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.json()["ok"] is True
    assert events == ["enter", "exit"]


def test_dependency_cleanup_runs_on_handler_error():
    class Resource:
        pass

    events: list[str] = []

    @contextmanager
    def provide_resource():
        events.append("enter")
        yield Resource()
        events.append("exit")

    async def fail(resource: Resource):
        raise HTTPError(400, "boom")

    router = Router()
    router.provide(Resource, provide_resource)
    router.get("/r", fail)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.status == 400
    assert events == ["enter", "exit"]


def test_dependency_asynccontextmanager_cleanup_runs():
    class Resource:
        pass

    events: list[str] = []

    @asynccontextmanager
    async def provide_resource():
        events.append("aenter")
        yield Resource()
        events.append("aexit")

    async def read(resource: Resource):
        return {"ok": isinstance(resource, Resource)}

    router = Router()
    router.provide(Resource, provide_resource)
    router.get("/r", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.json()["ok"] is True
    assert events == ["aenter", "aexit"]


def test_dependency_close_and_close_order_is_lifo():
    events: list[str] = []

    class A:
        def close(self) -> None:
            events.append("A.close")

    class B:
        def close(self) -> None:
            events.append("B.close")

    def provide_a() -> A:
        return A()

    def provide_b(a: A) -> B:
        return B()

    async def read(b: B):
        return {"ok": True}

    router = Router()
    router.provide(A, provide_a)
    router.provide(B, provide_b)
    router.get("/r", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.json()["ok"] is True
    assert events == ["B.close", "A.close"]


def test_dependency_aclose_coroutine_function_runs():
    events: list[str] = []

    class Resource:
        async def aclose(self) -> None:
            events.append("aclose")

    def provide_resource() -> Resource:
        return Resource()

    async def read(resource: Resource):
        return {"ok": True}

    router = Router()
    router.provide(Resource, provide_resource)
    router.get("/r", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.json()["ok"] is True
    assert events == ["aclose"]


def test_dependency_aclose_returning_awaitable_runs():
    events: list[str] = []

    class Resource:
        def aclose(self):
            async def _inner() -> None:
                events.append("aclose")

            return _inner()

    def provide_resource() -> Resource:
        return Resource()

    async def read(resource: Resource):
        return {"ok": True}

    router = Router()
    router.provide(Resource, provide_resource)
    router.get("/r", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.json()["ok"] is True
    assert events == ["aclose"]


def test_depends_use_cache_false_creates_multiple_and_cleans_both_lifo():
    events: list[str] = []

    class Resource:
        def __init__(self, key: int) -> None:
            self.key = key

        def close(self) -> None:
            events.append(f"close:{self.key}")

    counter = {"count": 0}

    def provide_resource() -> Resource:
        counter["count"] += 1
        return Resource(counter["count"])

    async def read(
        r1: Annotated[Resource, Depends(provide_resource, use_cache=False)],
        r2: Annotated[Resource, Depends(provide_resource, use_cache=False)],
    ):
        return {"same": r1 is r2}

    router = Router()
    router.get("/r", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.json()["same"] is False
    assert events == ["close:2", "close:1"]


def test_optional_type_dependency_without_provider_returns_none():
    class Database:
        pass

    async def read(db: Database | None):
        return {"none": db is None}

    router = Router()
    router.get("/r", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.json()["none"] is True


def test_default_value_used_when_provider_missing():
    class Database:
        def __init__(self, name: str) -> None:
            self.name = name

    default_db = Database("default")

    async def read(db: Database = default_db):
        return {"name": db.name}

    router = Router()
    router.get("/r", read)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/r")

    assert resp.json()["name"] == "default"


def test_duplicate_provider_registration_raises():
    class Database:
        pass

    def provide_db() -> Database:
        return Database()

    router = Router()
    router.provide(Database, provide_db)
    with pytest.raises(ValueError):
        router.provide(Database, provide_db)


def test_dependency_does_not_register_cleanup_without_exit_stack():
    events: list[str] = []

    class Resource:
        def close(self) -> None:
            events.append("close")

    def provide_resource() -> Resource:
        return Resource()

    async def read(resource: Resource):
        return {"ok": True}

    router = Router()
    router.provide(Resource, provide_resource)
    router.get("/r", read)

    handler, params = router.match("GET", "/r")
    assert handler is not None

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        scope={"type": "http", "method": "GET", "path": "/r", "headers": [], "query_string": b""},
        receive=receive,
        state={},
        exit_stack=None,
    )

    result = asyncio.run(handler(request, params))
    assert result["ok"] is True
    assert events == []


def test_include_router_merges_providers_global():
    class Database:
        def __init__(self, name: str) -> None:
            self.name = name

    def provide_parent_db() -> Database:
        return Database("parent")

    child = Router()

    async def from_parent(db: Database):
        return {"name": db.name}

    child.get("/child", from_parent)

    parent = Router()
    parent.provide(Database, provide_parent_db)
    parent.include_router(child, prefix="/api")
    app = BardApp(parent)

    with TestClient(app) as client:
        resp = client.get("/api/child")

    assert resp.json()["name"] == "parent"


def test_include_router_allows_parent_routes_to_use_child_providers():
    class Config:
        def __init__(self, token: str) -> None:
            self.token = token

    def provide_config() -> Config:
        return Config("child")

    child = Router()
    child.provide(Config, provide_config)

    parent = Router()
    parent.include_router(child, prefix="/api")

    async def read_config(cfg: Config):
        return {"token": cfg.token}

    parent.get("/cfg", read_config)
    app = BardApp(parent)

    with TestClient(app) as client:
        resp = client.get("/cfg")

    assert resp.json()["token"] == "child"


def test_missing_type_provider_raises_type_error():
    class Missing:
        pass

    async def read(value: Missing):
        return {"ok": True}

    router = Router()

    router.get("/missing", read)
    with pytest.raises(TypeError):
        BardApp(router)
