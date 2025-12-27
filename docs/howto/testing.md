# Testing

Use the in-process `TestClient`:

```python
from bard import BardApp, Router, TestClient


async def root():
    return {"ok": True}


router = Router()
router.get("/", root)
app = BardApp(router)


def test_root():
    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status == 200
        assert resp.json()["ok"] is True
```

Run:

```bash
uv run python -m pytest
```

## See Also

- [TestClient and event loops](../advanced/testclient.md)
