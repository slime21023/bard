from __future__ import annotations

from contextlib import AsyncExitStack
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from .errors import HTTPError
from .request import Request
from .response import Response, to_response
from .router import Router
from .utils import encode_json
from .websocket import WebSocket


class BardApp:
    def __init__(self, router: Router, lifespan=None) -> None:
        self.router = router
        self.lifespan = lifespan
        self.state: dict[str, Any] = {}
        self._http_middlewares: list[Callable[[Request, Callable[[], Awaitable[Any]]], Awaitable[Any]]] = []
        self._ws_middlewares: list[Callable[[WebSocket, Callable[[], Awaitable[Any]]], Awaitable[Any]]] = []
        self._exception_handlers: dict[type[BaseException], Callable[[Any, BaseException], Any]] = {}
        self._lifespan_cm = None
        self._lifespan_active = False
        self.router.compile()

    def provide(self, key: object, provider, *, use_cache: bool = True) -> None:
        self.router.provide(key, provider, use_cache=use_cache)

    def add_middleware(
        self,
        middleware: Callable[[Request, Callable[[], Awaitable[Any]]], Awaitable[Any]],
    ) -> None:
        self._http_middlewares.append(middleware)

    def add_websocket_middleware(
        self,
        middleware: Callable[[WebSocket, Callable[[], Awaitable[Any]]], Awaitable[Any]],
    ) -> None:
        self._ws_middlewares.append(middleware)

    def add_exception_handler(
        self,
        exc_type: type[BaseException],
        handler: Callable[[Any, BaseException], Any],
    ) -> None:
        self._exception_handlers[exc_type] = handler

    async def __call__(self, scope, receive, send) -> None:
        scope_type = scope.get("type")
        if scope_type == "http":
            await self._handle_http(scope, receive, send)
            return
        if scope_type == "lifespan":
            await self._handle_lifespan(receive, send)
            return
        if scope_type == "websocket":
            await self._handle_websocket(scope, receive, send)
            return

    async def _handle_http(self, scope, receive, send) -> None:
        async with AsyncExitStack() as exit_stack:
            request = Request(scope, receive, self.state, exit_stack=exit_stack)
            handler, params = self.router.match(scope.get("method", ""), scope.get("path", ""))
            if handler is None:
                await Response(b"Not Found", status=404)(send)
                return

            try:
                result = await self._dispatch_http(request, handler, params)
                response = to_response(result)
                await response(send)
                return
            except HTTPError as exc:
                await self._send_error(send, exc.detail, exc.status_code, headers=exc.headers)
                return
            except Exception as exc:
                handled = await self._handle_exception(request, exc)
                if handled is not None:
                    try:
                        response = to_response(handled)
                        await response(send)
                        return
                    except Exception:
                        pass
                await self._send_error(send, "Internal Server Error", 500)
                return

    async def _handle_lifespan(self, receive, send) -> None:
        message = await receive()
        if message.get("type") != "lifespan.startup":
            return

        if self.lifespan is None:
            await send({"type": "lifespan.startup.complete"})
            await self._await_shutdown(receive, send)
            return

        try:
            await self._lifespan_startup()
        except Exception as exc:
            await send({"type": "lifespan.startup.failed", "message": str(exc)})
            return

        await send({"type": "lifespan.startup.complete"})
        await self._await_shutdown(receive, send)

    async def _handle_websocket(self, scope, receive, send) -> None:
        message = await receive()
        if message.get("type") != "websocket.connect":
            return

        async with AsyncExitStack() as exit_stack:
            ws = WebSocket(scope, receive, send, self.state, exit_stack=exit_stack)
            handler, params = self.router.match("WEBSOCKET", scope.get("path", ""))
            if handler is None:
                await ws.close(code=1000)
                return
            await ws.accept()
            try:
                await self._dispatch_websocket(ws, handler, params)
            except Exception as exc:
                handled = await self._handle_exception(ws, exc)
                if handled is not None:
                    return
                await ws.close(code=1011)
                return
            finally:
                if not ws.closed:
                    await ws.close(code=1000)

    async def _await_shutdown(self, receive, send) -> None:
        message = await receive()
        if message.get("type") != "lifespan.shutdown":
            return
        try:
            await self._lifespan_shutdown()
        except Exception as exc:
            await send({"type": "lifespan.shutdown.failed", "message": str(exc)})
            return
        await send({"type": "lifespan.shutdown.complete"})

    async def startup(self) -> None:
        await self._lifespan_startup()

    async def shutdown(self) -> None:
        await self._lifespan_shutdown()

    async def _lifespan_startup(self) -> None:
        if self.lifespan is None or self._lifespan_active:
            return
        self._lifespan_cm = self.lifespan(self)
        await self._lifespan_cm.__aenter__()
        self._lifespan_active = True

    async def _lifespan_shutdown(self) -> None:
        if not self._lifespan_active or self._lifespan_cm is None:
            return
        await self._lifespan_cm.__aexit__(None, None, None)
        self._lifespan_active = False

    async def _send_error(
        self,
        send,
        detail: str,
        status: int,
        headers: dict[str, str] | None = None,
    ) -> None:
        response = Response(
            encode_json({"detail": detail}),
            status=status,
            headers=headers,
            media_type="application/json",
        )
        await response(send)

    async def _dispatch_http(self, request: Request, handler, params: dict[str, str]) -> Any:
        async def endpoint() -> Any:
            return await handler(request, params)

        route_middlewares = getattr(handler, "middlewares", ())
        all_middlewares = [*self._http_middlewares, *route_middlewares]

        call_next = endpoint
        for middleware in reversed(all_middlewares):
            next_call = call_next

            async def call_next_bound(
                middleware=middleware,
                next_call=next_call,
            ) -> Any:
                return await middleware(request, next_call)

            call_next = call_next_bound

        return await call_next()

    async def _handle_exception(self, request: Any, exc: BaseException) -> Any | None:
        for exc_type in type(exc).__mro__:
            handler = self._exception_handlers.get(exc_type)
            if handler is None:
                continue
            result = handler(request, exc)
            if inspect.isawaitable(result):
                return await result
            return result
        return None

    async def _dispatch_websocket(self, ws: WebSocket, handler, params: dict[str, str]) -> Any:
        async def endpoint() -> Any:
            return await handler(ws, params)

        route_middlewares = getattr(handler, "middlewares", ())
        all_middlewares = [*self._ws_middlewares, *route_middlewares]

        call_next = endpoint
        for middleware in reversed(all_middlewares):
            next_call = call_next

            async def call_next_bound(
                middleware=middleware,
                next_call=next_call,
            ) -> Any:
                return await middleware(ws, next_call)

            call_next = call_next_bound

        return await call_next()
