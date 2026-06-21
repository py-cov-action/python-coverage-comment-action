from __future__ import annotations

import pytest

from coverage_comment import json


def test_dumps():
    assert json.dumps({"hello": ["world", 42]}) == '{"hello": ["world", 42]}'


def test_loads():
    assert json.loads('{"hello": ["world", 42]}') == {"hello": ["world", 42]}


def test_loads__error():
    with pytest.raises(json.JSONDecodeError) as exc_info:
        json.loads("a")

    assert exc_info.value.__notes__ == ["Full string that triggered JSONDecodeError: a"]


def test_loads_dict():
    assert json.loads_dict('{"hello": ["world", 42]}') == {"hello": ["world", 42]}


def test_loads_dict__error():
    with pytest.raises(json.UnexpectedType):
        json.loads_dict("[]")
