from __future__ import annotations

from bard import BardApp, Request, Router, TestClient


def test_exception_handler_overrides_default_500():
    async def fail():
        raise RuntimeError("boom")

    def handle_runtime_error(request: Request, exc: BaseException):
        return {"detail": str(exc)}, 418

    router = Router()
    router.get("/fail", fail)
    app = BardApp(router)
    app.add_exception_handler(RuntimeError, handle_runtime_error)

    with TestClient(app) as client:
        resp = client.get("/fail")

    assert resp.status == 418
    assert resp.json()["detail"] == "boom"
