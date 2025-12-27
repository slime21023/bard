# Routing Details

## Matching Rules

- Static segments win over parameter segments.
- `HEAD` falls back to `GET` if no explicit `HEAD` handler exists.
- Trailing slashes and repeated slashes are normalized by the router.

```python
from typing import Annotated

from bard import BardApp, Path, Router, TestClient


async def me():
    return {"route": "me"}


async def by_id(user_id: Annotated[int, Path]):
    return {"route": "id", "id": user_id}


router = Router()
router.get("/users/me", me)
router.get("/users/{user_id}", by_id)
app = BardApp(router)


if __name__ == "__main__":
    with TestClient(app) as client:
        assert client.get("/users/me").json()["route"] == "me"
        assert client.get("/users/42").json()["id"] == 42
        assert client.request("HEAD", "/users/me").status == 200
        assert client.get("/users//me").json()["route"] == "me"
        assert client.get("/users/me/").json()["route"] == "me"
    print("ok")
```

## Subrouters and Prefixes

`include_router()` re-registers the child router under a prefix.

- `prefix="/api"` + child route `"/ping"` => `"/api/ping"`
- `prefix="/api"` + child route `"/"` => `"/api"`

