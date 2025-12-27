from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from types import UnionType
from typing import Any, Annotated, Union, get_args, get_origin, get_type_hints

import msgspec

from .di import Depends, ProviderRegistry, enter_resource
from .errors import HTTPError
from .extractors import File, Form, Header, Json, Path, Query, State, normalize_extractor
from .form import FormData, UploadFile
from .request import Request
from .utils import convert_value, decode_json, is_optional_type
from .websocket import WebSocket

try:
    from pydantic import ValidationError as PydanticValidationError
except Exception:  # pragma: no cover - optional at runtime
    PydanticValidationError = None

_MISSING = object()


Resolver = Callable[[Request, dict[str, str]], Awaitable[Any]]


class MissingProviderError(TypeError):
    pass


class CompiledHandler:
    def __init__(self, handler, resolvers: list[tuple[str, Any]]):
        self._handler = handler
        self._resolvers = resolvers

    async def __call__(self, request: Request, path_params: dict[str, str]):
        kwargs = {}
        for name, resolver in self._resolvers:
            kwargs[name] = await resolver(request, path_params)
        result = self._handler(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result


def compile_handler(
    handler,
    *,
    localns: dict[str, Any] | None = None,
    providers: ProviderRegistry | None = None,
    compiled_cache: dict[Callable, CompiledHandler] | None = None,
) -> CompiledHandler:
    signature = inspect.signature(handler)
    type_hints = _resolve_type_hints(handler, localns=localns)
    resolvers: list[tuple[str, Any]] = []

    for param in signature.parameters.values():
        if param.kind not in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
            raise TypeError(f"Unsupported parameter kind for {param.name}")
        annotation = type_hints.get(param.name, param.annotation)
        resolver = _compile_param(
            param,
            annotation,
            providers,
            compiled_cache=compiled_cache,
            callsite_localns=localns,
        )
        resolvers.append((param.name, resolver))

    return CompiledHandler(handler, resolvers)


def _resolve_type_hints(handler, localns: dict[str, Any] | None = None) -> dict[str, Any]:
    resolved_locals: dict[str, Any] = {}
    if handler.__closure__:
        for name, cell in zip(handler.__code__.co_freevars, handler.__closure__):
            try:
                resolved_locals[name] = cell.cell_contents
            except ValueError:
                continue
    if localns:
        resolved_locals.update(localns)
    try:
        return get_type_hints(
            handler,
            globalns=handler.__globals__,
            localns=resolved_locals,
            include_extras=True,
        )
    except Exception as exc:
        raise TypeError(f"Failed to resolve type hints for {handler}") from exc


def _compile_param(
    param: inspect.Parameter,
    annotation: Any,
    providers: ProviderRegistry | None,
    *,
    compiled_cache: dict[Callable, CompiledHandler] | None,
    callsite_localns: dict[str, Any] | None,
) -> Resolver:
    if annotation is inspect._empty:
        raise TypeError(f"Missing type annotation for {param.name}")

    default = param.default if param.default is not inspect._empty else _MISSING

    if annotation is Request or (
        isinstance(annotation, type) and issubclass(annotation, Request)
    ):

        async def resolve_request(request: Request, path_params: dict[str, str]) -> Request:
            return request

        return resolve_request

    if annotation is WebSocket or (
        isinstance(annotation, type) and issubclass(annotation, WebSocket)
    ):

        async def resolve_ws(request: Request, path_params: dict[str, str]) -> WebSocket:
            return request  # type: ignore[return-value]

        return resolve_ws

    origin = get_origin(annotation)
    extractor = None
    depends: Depends | None = None
    target_type = annotation

    if origin is Annotated:
        target_type, *metadata = get_args(annotation)
        for meta in metadata:
            if depends is None and isinstance(meta, Depends):
                depends = meta
                continue
            extractor = normalize_extractor(meta)
            if extractor is not None:
                break

    if extractor is None:
        if depends is not None:
            return _compile_dependency(
                param.name,
                target_type,
                depends.provider,
                default=default,
                cache_key=("depends", depends.provider),
                use_cache=depends.use_cache,
                providers=providers,
                localns=callsite_localns,
                compiled_cache=compiled_cache,
            )
        return _compile_type_dependency(
            param.name,
            target_type,
            default=default,
            providers=providers,
            compiled_cache=compiled_cache,
        )

    if isinstance(extractor, Json):

        async def resolve_json(request: Request, path_params: dict[str, str]) -> Any:
            body = await request.body()
            if not body:
                return _default_or_error(param.name, default, target_type)
            try:
                return decode_json(body, target_type)
            except (msgspec.DecodeError, msgspec.ValidationError) as exc:
                raise HTTPError(422, f"Invalid JSON for {param.name}") from exc
            except Exception as exc:
                if PydanticValidationError and isinstance(exc, PydanticValidationError):
                    raise HTTPError(422, f"Invalid JSON for {param.name}") from exc
                raise

        return resolve_json

    if isinstance(extractor, Query):
        key = extractor.name or param.name

        async def resolve_query(request: Request, path_params: dict[str, str]) -> Any:
            values = request.query_params.get(key)
            if values is None:
                return _default_or_error(param.name, default, target_type)
            value = values if _is_list_type(target_type) else values[0]
            return _convert_or_error(value, target_type, f"Invalid query parameter {key}")

        return resolve_query

    if isinstance(extractor, Form):
        key = extractor.name or param.name

        async def resolve_form(request: Request, path_params: dict[str, str]) -> Any:
            try:
                form = await request.form()
            except Exception as exc:
                raise HTTPError(400, "Invalid form data") from exc
            if extractor.name is None:
                if target_type is FormData:
                    return form
                if target_type is dict or get_origin(target_type) is dict:
                    return _flatten_fields(form.fields)
            values = form.fields.get(key)
            if values is None:
                return _default_or_error(param.name, default, target_type)
            value = values if _is_list_type(target_type) else values[0]
            return _convert_or_error(value, target_type, f"Invalid form field {key}")

        return resolve_form

    if isinstance(extractor, File):
        key = extractor.name or param.name

        async def resolve_file(request: Request, path_params: dict[str, str]) -> Any:
            try:
                form = await request.form()
            except Exception as exc:
                raise HTTPError(400, "Invalid form data") from exc
            files = form.files.get(key)
            if files is None:
                return _default_or_error(param.name, default, target_type)
            if _is_list_type(target_type):
                item_type = _list_item_type(target_type)
                return [_coerce_file(file, item_type) for file in files]
            return _coerce_file(files[0], target_type)

        return resolve_file

    if isinstance(extractor, Path):
        key = extractor.name or param.name

        async def resolve_path(request: Request, path_params: dict[str, str]) -> Any:
            if key not in path_params:
                return _default_or_error(param.name, default, target_type)
            return _convert_or_error(path_params[key], target_type, f"Invalid path parameter {key}")

        return resolve_path

    if isinstance(extractor, Header):
        key = (extractor.name or param.name).lower()

        async def resolve_header(request: Request, path_params: dict[str, str]) -> Any:
            if key not in request.headers:
                return _default_or_error(param.name, default, target_type)
            return _convert_or_error(request.headers[key], target_type, f"Invalid header {key}")

        return resolve_header

    if isinstance(extractor, State):
        key = extractor.name or param.name

        async def resolve_state(request: Request, path_params: dict[str, str]) -> Any:
            if key not in request.state:
                return _default_or_error(param.name, default, target_type)
            return request.state[key]

        return resolve_state

    raise TypeError(f"Unsupported extractor for {param.name}")


def _compile_type_dependency(
    name: str,
    target_type: Any,
    *,
    default: Any,
    providers: ProviderRegistry | None,
    compiled_cache: dict[Callable, CompiledHandler] | None,
) -> Resolver:
    if providers is None:
        raise TypeError(f"Missing extractor for {name}")

    is_optional, inner = is_optional_type(target_type)
    key = inner if is_optional else target_type
    spec = providers.get(key)
    if spec is None:
        if default is not _MISSING:
            async def resolve_default(request: Request, path_params: dict[str, str]) -> Any:
                return default

            return resolve_default
        if is_optional:
            async def resolve_none(request: Request, path_params: dict[str, str]) -> Any:
                return None

            return resolve_none
        if _is_request_data_type(key):
            raise TypeError(f"Missing extractor for {name}")
        raise MissingProviderError(f"Missing extractor or provider for {name}")

    return _compile_dependency(
        name,
        key,
        spec.provider,
        default=default,
        cache_key=key,
        use_cache=spec.use_cache,
        providers=providers,
        localns=spec.localns,
        compiled_cache=compiled_cache,
    )


def _compile_dependency(
    name: str,
    target_type: Any,
    provider,
    *,
    default: Any,
    cache_key: object,
    use_cache: bool,
    providers: ProviderRegistry | None,
    localns: dict[str, Any] | None,
    compiled_cache: dict[Callable, CompiledHandler] | None,
) -> Resolver:
    if compiled_cache is not None and provider in compiled_cache:
        compiled_provider = compiled_cache[provider]
    else:
        compiled_provider = compile_handler(
            provider,
            localns=localns,
            providers=providers,
            compiled_cache=compiled_cache,
        )
        if compiled_cache is not None:
            compiled_cache[provider] = compiled_provider

    async def resolve(request: Request, path_params: dict[str, str]) -> Any:
        if not use_cache:
            value = await compiled_provider(request, path_params)
            return await enter_resource(request.exit_stack, value)
        if cache_key in request.di_cache:
            return request.di_cache[cache_key]
        value = await compiled_provider(request, path_params)
        resource = await enter_resource(request.exit_stack, value)
        request.di_cache[cache_key] = resource
        return resource

    return resolve


def _default_or_error(name: str, default: Any, target_type: Any) -> Any:
    is_optional, _ = is_optional_type(target_type)
    if default is not _MISSING:
        return default
    if is_optional:
        return None
    raise HTTPError(422, f"Missing required value for {name}")


def _is_request_data_type(annotation: Any) -> bool:
    if annotation in (Any, str, int, float, bool, bytes, dict, list):
        return True
    origin = get_origin(annotation)
    if origin in (list, dict, Union, UnionType):
        return True
    return False


def _is_list_type(target_type: Any) -> bool:
    is_optional, inner = is_optional_type(target_type)
    target = inner if is_optional else target_type
    return get_origin(target) is list


def _list_item_type(target_type: Any) -> Any:
    is_optional, inner = is_optional_type(target_type)
    target = inner if is_optional else target_type
    args = get_args(target)
    return args[0] if args else Any


def _coerce_file(upload: UploadFile, target_type: Any) -> Any:
    if target_type is UploadFile or isinstance(upload, target_type):
        return upload
    if target_type is bytes:
        return upload.content
    if target_type is str:
        return upload.text()
    return _convert_or_error(upload.content, target_type, "Invalid file payload")


def _flatten_fields(fields: dict[str, list[str]]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, values in fields.items():
        if len(values) == 1:
            flattened[key] = values[0]
        else:
            flattened[key] = list(values)
    return flattened


def _convert_or_error(value: Any, target_type: Any, message: str) -> Any:
    try:
        return convert_value(value, target_type)
    except Exception as exc:
        raise HTTPError(422, message) from exc
