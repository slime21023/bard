from __future__ import annotations

from dataclasses import dataclass
import inspect
from typing import Callable, Any

from .handler import CompiledHandler, MissingProviderError, compile_handler
from .di import ProviderRegistry
from .request import Request
from .websocket import WebSocket


@dataclass
class _Node:
    static_children: dict[str, "_Node"]
    param_child: "_Node | None"
    handlers: dict[str, Callable]
    compiled: dict[str, CompiledHandler]
    routed: dict[str, "_RoutedHandler"]
    param_names: dict[str, list[str]]
    middlewares: dict[str, list[Callable]]

    def __init__(self) -> None:
        self.static_children = {}
        self.param_child = None
        self.handlers = {}
        self.compiled = {}
        self.routed = {}
        self.param_names = {}
        self.middlewares = {}


@dataclass(frozen=True, slots=True)
class _RouteSpec:
    path: str
    handler: Callable
    methods: tuple[str, ...]
    middlewares: list[Callable]


class _RoutedHandler:
    def __init__(self, compiled: CompiledHandler, middlewares: list[Callable], *, is_websocket: bool) -> None:
        self._compiled = compiled
        self.middlewares = middlewares
        self.is_websocket = is_websocket

    async def __call__(self, request: Request | WebSocket, path_params: dict[str, str]):
        return await self._compiled(request, path_params)  # type: ignore[arg-type]


class Router:
    def __init__(self) -> None:
        self._root = _Node()
        self._routes: list[tuple[_Node, str]] = []
        self._compiled_cache: dict[Callable, CompiledHandler] = {}
        self._handler_localns: dict[Callable, dict[str, Any]] = {}
        self._providers = ProviderRegistry()
        self._route_specs: list[_RouteSpec] = []
        self._compiled_once = False
        self._http_middlewares: list[Callable] = []
        self._ws_middlewares: list[Callable] = []

    def provide(self, key: object, provider: Callable[..., Any], *, use_cache: bool = True) -> None:
        caller_locals = _get_callsite_locals()
        self._handler_localns.setdefault(provider, caller_locals)
        self._providers.provide(key, provider, use_cache=use_cache, localns=caller_locals)

    def add_middleware(self, middleware: Callable) -> None:
        self._http_middlewares.append(middleware)

    def add_websocket_middleware(self, middleware: Callable) -> None:
        self._ws_middlewares.append(middleware)

    def include_router(self, other: "Router", prefix: str = "") -> None:
        if prefix and not prefix.startswith("/"):
            raise ValueError("Prefix must start with '/'")
        prefix = prefix.rstrip("/")

        for key, spec in other._providers.items():
            if self._providers.get(key) is not None:
                raise ValueError(f"Provider already registered for {key!r}")
            self._providers.provide(
                key,
                spec.provider,
                use_cache=spec.use_cache,
                localns=spec.localns,
            )
            if spec.localns is not None:
                self._handler_localns.setdefault(spec.provider, spec.localns)

        for spec in other._route_specs:
            path = _join_prefix(prefix, spec.path)
            self.add_route(path, spec.handler, list(spec.methods), middlewares=spec.middlewares)

    def add_route(
        self,
        path: str,
        handler: Callable,
        methods: list[str],
        *,
        middlewares: list[Callable] | None = None,
    ) -> None:
        if not path.startswith("/"):
            raise ValueError("Route path must start with '/'")
        node = self._root
        param_names: list[str] = []
        for segment in _split_path(path):
            if _is_param(segment):
                name = segment[1:-1]
                param_names.append(name)
                if node.param_child is None:
                    node.param_child = _Node()
                node = node.param_child
            else:
                node = node.static_children.setdefault(segment, _Node())
        caller_locals = _get_callsite_locals()
        self._handler_localns.setdefault(handler, caller_locals)
        methods_tuple = tuple(methods)
        is_websocket = any(m.upper() == "WEBSOCKET" for m in methods_tuple)
        if middlewares is None:
            middlewares = self._ws_middlewares if is_websocket else self._http_middlewares
        self._route_specs.append(
            _RouteSpec(path=path, handler=handler, methods=methods_tuple, middlewares=middlewares)
        )
        compiled: CompiledHandler | None
        try:
            compiled = self._compile_handler_cached(handler, localns=caller_locals)
        except MissingProviderError:
            if self._compiled_once:
                raise
            compiled = None
        for method in methods:
            method_key = method.upper()
            if method_key in node.handlers:
                raise ValueError(f"Route already registered for {method_key} {path}")
            node.handlers[method_key] = handler
            node.param_names[method_key] = list(param_names)
            node.middlewares[method_key] = middlewares
            self._routes.append((node, method_key))
            if compiled is not None:
                node.compiled[method_key] = compiled
                node.routed[method_key] = _RoutedHandler(
                    compiled,
                    middlewares,
                    is_websocket=(method_key == "WEBSOCKET"),
                )

    def get(self, path: str, handler: Callable) -> None:
        self.add_route(path, handler, ["GET"])

    def post(self, path: str, handler: Callable) -> None:
        self.add_route(path, handler, ["POST"])

    def put(self, path: str, handler: Callable) -> None:
        self.add_route(path, handler, ["PUT"])

    def delete(self, path: str, handler: Callable) -> None:
        self.add_route(path, handler, ["DELETE"])

    def websocket(self, path: str, handler: Callable) -> None:
        self.add_route(path, handler, ["WEBSOCKET"])

    def compile(self) -> None:
        self._compiled_once = True
        for node, method in self._routes:
            handler = node.handlers[method]
            compiled = self._compile_handler_cached(handler)
            node.compiled[method] = compiled
            middlewares = node.middlewares.get(method, [])
            node.routed[method] = _RoutedHandler(
                compiled,
                middlewares,
                is_websocket=(method == "WEBSOCKET"),
            )

    def match(self, method: str, path: str) -> tuple[_RoutedHandler | None, dict[str, str]]:
        node = self._root
        param_values: list[str] = []
        for segment in _split_path(path):
            if segment in node.static_children:
                node = node.static_children[segment]
                continue
            if node.param_child is None:
                return None, {}
            param_values.append(segment)
            node = node.param_child
        method = method.upper()
        routed = node.routed.get(method)
        param_names = node.param_names.get(method, [])
        if routed is None and method == "HEAD":
            routed = node.routed.get("GET")
            param_names = node.param_names.get("GET", [])
        params = {name: value for name, value in zip(param_names, param_values)}
        return routed, params

    def _compile_handler_cached(
        self,
        handler: Callable,
        localns: dict[str, object] | None = None,
    ) -> CompiledHandler:
        stored_locals = self._handler_localns.get(handler)
        if stored_locals is not None:
            localns = stored_locals
        elif localns is not None:
            self._handler_localns[handler] = dict(localns)
        compiled = self._compiled_cache.get(handler)
        if compiled is None:
            compiled = compile_handler(
                handler,
                localns=localns,
                providers=self._providers,
                compiled_cache=self._compiled_cache,
            )
            self._compiled_cache[handler] = compiled
        return compiled


def _split_path(path: str) -> list[str]:
    trimmed = path.strip("/")
    if not trimmed:
        return []
    return [segment for segment in trimmed.split("/") if segment]


def _is_param(segment: str) -> bool:
    return segment.startswith("{") and segment.endswith("}") and len(segment) > 2


def _join_prefix(prefix: str, path: str) -> str:
    if not prefix:
        return path
    if path == "/":
        return prefix
    return prefix + path


def _get_callsite_locals() -> dict[str, object]:
    frame = inspect.currentframe()
    if frame is None:
        return {}
    try:
        frame = frame.f_back
        while frame and frame.f_code.co_filename == __file__:
            frame = frame.f_back
        return dict(frame.f_locals) if frame else {}
    finally:
        del frame
