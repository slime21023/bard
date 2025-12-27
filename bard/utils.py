from __future__ import annotations

from dataclasses import is_dataclass
from enum import Enum
from types import UnionType
from typing import Any, Union, get_args, get_origin

import msgspec


def is_optional_type(annotation: Any) -> tuple[bool, Any]:
    if annotation is type(None):
        return True, type(None)
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        args = get_args(annotation)
        if len(args) == 2 and type(None) in args:
            target = args[0] if args[1] is type(None) else args[1]
            return True, target
    return False, annotation


def convert_value(value: Any, target_type: Any) -> Any:
    if target_type is Any:
        return value
    is_optional, inner_type = is_optional_type(target_type)
    if is_optional and value is None:
        return None
    target_type = inner_type

    origin = get_origin(target_type)
    args = get_args(target_type)

    if target_type is list:
        return _convert_list(value, ())
    if target_type is dict:
        return _convert_dict(value)

    if origin is list:
        return _convert_list(value, args)

    if origin is dict:
        return _convert_dict(value)

    if origin in (Union, UnionType):
        return _convert_union(value, args)

    return _convert_scalar(value, target_type)


def decode_json(body: bytes, target_type: Any) -> Any:
    if target_type is Any:
        return msgspec.json.decode(body)
    if hasattr(target_type, "model_validate_json"):
        return target_type.model_validate_json(body)
    if is_dataclass(target_type):
        return msgspec.json.decode(body, type=target_type)
    return msgspec.json.decode(body, type=target_type)


def encode_json(data: Any) -> bytes:
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    return msgspec.json.encode(data)


def _convert_list(value: Any, args: tuple[Any, ...]) -> list[Any]:
    item_type = args[0] if args else Any
    if value is None:
        return []
    if isinstance(value, list):
        return [convert_value(item, item_type) for item in value]
    return [convert_value(value, item_type)]


def _convert_dict(value: Any) -> dict[Any, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    raise ValueError("Expected dict value")


def _convert_union(value: Any, args: tuple[Any, ...]) -> Any:
    last_error: Exception | None = None
    for arg in args:
        if arg is type(None):
            if value is None:
                return None
            continue
        try:
            return convert_value(value, arg)
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    return value


def _convert_scalar(value: Any, target_type: Any) -> Any:
    if target_type is str:
        return "" if value is None else str(value)
    if target_type is int:
        return int(value)
    if target_type is float:
        return float(value)
    if target_type is bool:
        return _coerce_bool(value)
    if target_type is bytes:
        if isinstance(value, bytes):
            return value
        return str(value).encode("utf-8")
    if isinstance(target_type, type) and issubclass(target_type, Enum):
        return target_type(value)
    if isinstance(value, target_type):
        return value
    return target_type(value)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    return bool(value)
