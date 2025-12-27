# TestClient & Event Loops

`TestClient` runs the app in-process and triggers lifespan by default.

## Event Loop Constraint

`TestClient` cannot run inside an already-running event loop. If you are inside `asyncio`, use a real ASGI server for integration testing.

