from __future__ import annotations

import pytest
from pydantic import BaseModel

from dataclasses import dataclass
from typing import Any, Optional

from bard.utils import (
    _convert_union,
    convert_value,
    decode_json,
    encode_json,
    is_optional_type,
)


def test_encode_json_pydantic_model_dump():
    class User(BaseModel):
        id: int
        name: str

    user = User(id=1, name="demo")
    encoded = encode_json(user)
    decoded = decode_json(encoded, dict)

    assert decoded == {"id": 1, "name": "demo"}


def test_convert_value_bytes():
    assert convert_value("abc", bytes) == b"abc"
    assert convert_value(b"xyz", bytes) == b"xyz"


def test_convert_value_list_from_scalar():
    assert convert_value("1", list[int]) == [1]
    assert convert_value(None, list[int]) == []
    assert convert_value("1", list) == ["1"]


def test_convert_value_dict_type_error():
    with pytest.raises(ValueError):
        convert_value("not-a-dict", dict)


def test_convert_value_dict_none_and_dict():
    assert convert_value(None, dict) == {}
    assert convert_value({"ok": True}, dict) == {"ok": True}
    assert convert_value({"ok": True}, dict[str, int]) == {"ok": True}


def test_decode_json_any_roundtrip():
    payload = {"hello": "bard"}
    encoded = encode_json(payload)
    decoded = decode_json(encoded, Any)

    assert decoded["hello"] == "bard"


def test_convert_value_bool_yes_no():
    assert convert_value("yes", bool) is True
    assert convert_value("no", bool) is False


def test_is_optional_type_none():
    assert is_optional_type(type(None))[0] is True


def test_convert_value_any():
    payload = {"hello": "bard"}

    assert convert_value(payload, Any) is payload


def test_convert_value_optional_none():
    assert convert_value(None, Optional[int]) is None


def test_convert_union_all_failures_raise():
    with pytest.raises(ValueError):
        convert_value("not-a-number", int | float)


def test_convert_union_none_value():
    assert convert_value(None, Optional[str]) is None
    assert convert_value(None, int | None | str) is None


def test_convert_scalar_instance_passthrough():
    @dataclass
    class Item:
        value: int

    item = Item(value=1)

    assert convert_value(item, Item) is item


def test_convert_bool_fallback():
    assert convert_value("maybe", bool) is True


def test_convert_scalar_constructor_fallback():
    @dataclass
    class Wrapper:
        value: int

        def __init__(self, value):
            self.value = int(value)

    wrapped = convert_value("7", Wrapper)

    assert wrapped.value == 7


def test_convert_union_returns_value_on_all_none():
    assert _convert_union("text", (type(None),)) == "text"


def test_convert_bool_identity():
    assert convert_value(True, bool) is True
