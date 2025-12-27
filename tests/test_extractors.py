from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

import msgspec
from pydantic import BaseModel

from bard import BardApp, Header, Json, Path, Query, Router, State, TestClient
from bard.extractors import normalize_extractor


class CreateUser(msgspec.Struct):
    username: str
    email: str


@dataclass
class DataPayload:
    name: str


class PydanticUser(BaseModel):
    id: int
    name: str


class Color(Enum):
    RED = "red"
    BLUE = "blue"


def test_extractor_repr_includes_name():
    extractor = Header("x-test")

    assert "Header" in repr(extractor)
    assert "x-test" in repr(extractor)


def test_normalize_extractor_with_class():
    normalized = normalize_extractor(Query)

    assert isinstance(normalized, Query)


def test_normalize_extractor_unknown_returns_none():
    assert normalize_extractor(object()) is None


def test_json_extractor_msgspec():
    async def create_user(payload: Annotated[CreateUser, Json]):
        return {"user": payload.username}, 201

    router = Router()
    router.post("/users", create_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.post("/users", json={"username": "demo", "email": "d@example.com"})

    assert resp.status == 201
    assert resp.json()["user"] == "demo"


def test_json_invalid_returns_422():
    async def create_user(payload: Annotated[CreateUser, Json]):
        return {"user": payload.username}

    router = Router()
    router.post("/users", create_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.request("POST", "/users", body=b"{")

    assert resp.status == 422
    assert "Invalid JSON" in resp.json()["detail"]


def test_json_missing_body_returns_422():
    async def create_user(payload: Annotated[CreateUser, Json]):
        return {"user": payload.username}

    router = Router()
    router.post("/users", create_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.request("POST", "/users")

    assert resp.status == 422
    assert "Missing required value" in resp.json()["detail"]


def test_json_optional_body_defaults_to_none():
    async def create_user(payload: Annotated[CreateUser | None, Json]):
        return {"payload": payload}

    router = Router()
    router.post("/users", create_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.request("POST", "/users")

    assert resp.json()["payload"] is None


def test_dataclass_json_extractor():
    async def create(payload: Annotated[DataPayload, Json]):
        return {"name": payload.name}

    router = Router()
    router.post("/payloads", create)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.post("/payloads", json={"name": "demo"})

    assert resp.json()["name"] == "demo"


def test_local_dataclass_annotation_resolves():
    @dataclass
    class LocalPayload:
        name: str

    async def create(payload: Annotated[LocalPayload, Json]):
        return {"name": payload.name}

    router = Router()
    router.post("/payloads", create)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.post("/payloads", json={"name": "local"})

    assert resp.json()["name"] == "local"


def test_pydantic_json_validation_error_returns_422():
    async def create_user(payload: Annotated[PydanticUser, Json]):
        return {"id": payload.id}

    router = Router()
    router.post("/users", create_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.post("/users", json={"name": "demo"})

    assert resp.status == 422
    assert "Invalid JSON" in resp.json()["detail"]


def test_pydantic_json_valid_payload():
    async def create_user(payload: Annotated[PydanticUser, Json]):
        return {"id": payload.id, "name": payload.name}

    router = Router()
    router.post("/users", create_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.post("/users", json={"id": 7, "name": "demo"})

    assert resp.json()["id"] == 7
    assert resp.json()["name"] == "demo"


def test_query_header_path_state_extractors():
    async def get_user(
        user_id: Annotated[int, Path],
        q: Annotated[str, Query],
        agent: Annotated[str, Header("user-agent")],
        db: Annotated[str, State("db")],
    ):
        return {"user_id": user_id, "q": q, "agent": agent, "db": db}

    router = Router()
    router.get("/users/{user_id}", get_user)
    app = BardApp(router)
    app.state["db"] = "sqlite"

    with TestClient(app) as client:
        resp = client.get("/users/42?q=hello", headers={"user-agent": "pytest"})

    data = resp.json()
    assert data["user_id"] == 42
    assert data["q"] == "hello"
    assert data["agent"] == "pytest"
    assert data["db"] == "sqlite"


def test_query_list_values():
    async def search(tags: Annotated[list[str], Query("tag")]):
        return {"tags": tags}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?tag=a&tag=b")

    assert resp.json()["tags"] == ["a", "b"]


def test_query_list_single_value():
    async def search(tags: Annotated[list[str], Query("tag")]):
        return {"tags": tags}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?tag=one")

    assert resp.json()["tags"] == ["one"]


def test_query_list_int_values():
    async def search(ids: Annotated[list[int], Query("id")]):
        return {"ids": ids}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?id=1&id=2")

    assert resp.json()["ids"] == [1, 2]


def test_query_multi_value_first_entry():
    async def search(tag: Annotated[str, Query("tag")]):
        return {"tag": tag}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?tag=first&tag=second")

    assert resp.json()["tag"] == "first"


def test_query_blank_value_preserved():
    async def search(q: Annotated[str, Query]):
        return {"q": q}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?q=")

    assert resp.json()["q"] == ""


def test_query_bool_values():
    async def flags(active: Annotated[bool, Query]):
        return {"active": active}

    router = Router()
    router.get("/flags", flags)
    app = BardApp(router)

    with TestClient(app) as client:
        true_resp = client.get("/flags?active=true")
        false_resp = client.get("/flags?active=false")

    assert true_resp.json()["active"] is True
    assert false_resp.json()["active"] is False


def test_query_bool_numeric_values():
    async def flags(active: Annotated[bool, Query]):
        return {"active": active}

    router = Router()
    router.get("/flags", flags)
    app = BardApp(router)

    with TestClient(app) as client:
        true_resp = client.get("/flags?active=1")
        false_resp = client.get("/flags?active=0")

    assert true_resp.json()["active"] is True
    assert false_resp.json()["active"] is False


def test_query_bool_yes_no_values():
    async def flags(active: Annotated[bool, Query]):
        return {"active": active}

    router = Router()
    router.get("/flags", flags)
    app = BardApp(router)

    with TestClient(app) as client:
        true_resp = client.get("/flags?active=yes")
        false_resp = client.get("/flags?active=no")

    assert true_resp.json()["active"] is True
    assert false_resp.json()["active"] is False


def test_query_float_conversion():
    async def prices(amount: Annotated[float, Query]):
        return {"amount": amount}

    router = Router()
    router.get("/prices", prices)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/prices?amount=1.25")

    assert resp.json()["amount"] == 1.25


def test_query_optional_int_missing():
    async def search(page: Annotated[int | None, Query]):
        return {"page": page}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search")

    assert resp.json()["page"] is None


def test_query_optional_int_present():
    async def search(page: Annotated[int | None, Query]):
        return {"page": page}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?page=5")

    assert resp.json()["page"] == 5


def test_query_negative_int():
    async def search(page: Annotated[int, Query]):
        return {"page": page}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?page=-5")

    assert resp.json()["page"] == -5


def test_query_float_negative():
    async def prices(amount: Annotated[float, Query]):
        return {"amount": amount}

    router = Router()
    router.get("/prices", prices)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/prices?amount=-1.25")

    assert resp.json()["amount"] == -1.25


def test_query_bytes_conversion():
    async def echo(token: Annotated[bytes, Query]):
        return {"token": token.decode("utf-8")}

    router = Router()
    router.get("/query", echo)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/query?token=abc")

    assert resp.json()["token"] == "abc"


def test_query_list_optional_item():
    async def search(tags: Annotated[list[int | None], Query("tag")]):
        return {"tags": tags}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?tag=1&tag=2")

    assert resp.json()["tags"] == [1, 2]


def test_query_union_prefers_int():
    async def search(value: Annotated[int | str, Query]):
        return {"value": value}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?value=5")

    assert resp.json()["value"] == 5


def test_query_enum_conversion():
    async def paint(color: Annotated[Color, Query]):
        return {"color": color.value}

    router = Router()
    router.get("/paint", paint)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/paint?color=red")

    assert resp.json()["color"] == "red"


def test_query_enum_invalid_returns_422():
    async def paint(color: Annotated[Color, Query]):
        return {"color": color.value}

    router = Router()
    router.get("/paint", paint)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/paint?color=green")

    assert resp.status == 422
    assert "Invalid query parameter" in resp.json()["detail"]


def test_query_union_falls_back_to_str():
    async def search(value: Annotated[int | str, Query]):
        return {"value": value}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?value=text")

    assert resp.json()["value"] == "text"


def test_query_default_value():
    async def search(page: Annotated[int, Query] = 1):
        return {"page": page}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search")

    assert resp.json()["page"] == 1


def test_query_list_default_value():
    async def search(tags: Annotated[list[str], Query("tag")] = ["default"]):
        return {"tags": tags}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search")

    assert resp.json()["tags"] == ["default"]


def test_query_int_conversion_error_returns_422():
    async def search(page: Annotated[int, Query]):
        return {"page": page}

    router = Router()
    router.get("/search", search)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/search?page=bad")

    assert resp.status == 422
    assert "Invalid query parameter" in resp.json()["detail"]


def test_header_case_insensitive():
    async def echo(agent: Annotated[str, Header("X-Agent")]):
        return {"agent": agent}

    router = Router()
    router.get("/headers", echo)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/headers", headers={"x-agent": "probe"})

    assert resp.json()["agent"] == "probe"


def test_header_default_value_used():
    async def echo(agent: Annotated[str, Header("x-agent")] = "default"):
        return {"agent": agent}

    router = Router()
    router.get("/headers", echo)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/headers")

    assert resp.json()["agent"] == "default"


def test_header_bool_conversion():
    async def echo(active: Annotated[bool, Header("x-active")]):
        return {"active": active}

    router = Router()
    router.get("/headers", echo)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/headers", headers={"x-active": "true"})

    assert resp.json()["active"] is True


def test_header_int_invalid_returns_422():
    async def echo(count: Annotated[int, Header("x-count")]):
        return {"count": count}

    router = Router()
    router.get("/headers", echo)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/headers", headers={"x-count": "bad"})

    assert resp.status == 422
    assert "Invalid header" in resp.json()["detail"]


def test_header_bytes_conversion():
    async def echo(token: Annotated[bytes, Header("x-token")]):
        return {"token": token.decode("utf-8")}

    router = Router()
    router.get("/headers", echo)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/headers", headers={"x-token": "abc"})

    assert resp.json()["token"] == "abc"


def test_header_optional_defaults_to_none():
    async def echo(agent: Annotated[str | None, Header("x-agent")]):
        return {"agent": agent}

    router = Router()
    router.get("/headers", echo)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/headers")

    assert resp.json()["agent"] is None


def test_header_float_conversion():
    async def echo(ratio: Annotated[float, Header("x-ratio")]):
        return {"ratio": ratio}

    router = Router()
    router.get("/headers", echo)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/headers", headers={"x-ratio": "2.5"})

    assert resp.json()["ratio"] == 2.5


def test_path_conversion_error_returns_422():
    async def get_user(user_id: Annotated[int, Path]):
        return {"user_id": user_id}

    router = Router()
    router.get("/users/{user_id}", get_user)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/users/not-an-int")

    assert resp.status == 422
    assert "Invalid path parameter" in resp.json()["detail"]


def test_path_float_conversion():
    async def get_price(price: Annotated[float, Path]):
        return {"price": price}

    router = Router()
    router.get("/prices/{price}", get_price)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/prices/1.5")

    assert resp.json()["price"] == 1.5


def test_path_negative_int_conversion():
    async def get_id(item_id: Annotated[int, Path]):
        return {"item_id": item_id}

    router = Router()
    router.get("/items/{item_id}", get_id)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/items/-7")

    assert resp.json()["item_id"] == -7


def test_state_missing_returns_422():
    async def read_state(db: Annotated[str, State("db")]):
        return {"db": db}

    router = Router()
    router.get("/", read_state)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/")

    assert resp.status == 422
    assert "Missing required value" in resp.json()["detail"]


def test_state_default_value_used():
    async def read_state(db: Annotated[str, State("db")] = "memory"):
        return {"db": db}

    router = Router()
    router.get("/", read_state)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/")

    assert resp.json()["db"] == "memory"


def test_optional_query_defaults_to_none():
    async def optional_query(q: Annotated[str | None, Query]):
        return {"q": q}

    router = Router()
    router.get("/optional", optional_query)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/optional")

    assert resp.json()["q"] is None


def test_optional_state_defaults_to_none():
    async def read_state(db: Annotated[str | None, State("db")]):
        return {"db": db}

    router = Router()
    router.get("/", read_state)
    app = BardApp(router)

    with TestClient(app) as client:
        resp = client.get("/")

    assert resp.json()["db"] is None
