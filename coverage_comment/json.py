from __future__ import annotations

import json as python_json
from collections.abc import Mapping, Sequence
from json import JSONDecodeError as JSONDecodeError  # reexport error

type Json = dict[str, Json] | list[Json] | str | int | float | bool | None
type ROJson = Mapping[str, Json] | Sequence[Json] | str | int | float | bool | None


def dumps(obj: ROJson) -> str:
    return python_json.dumps(obj=obj)


def loads(serialized: str) -> Json:
    try:
        return python_json.loads(serialized)
    except python_json.JSONDecodeError as exc:
        exc.add_note(f"Full string that triggered JSONDecodeError: {serialized}")
        raise


class UnexpectedType(Exception):
    pass


def loads_dict(serialized: str) -> dict[str, Json]:
    result = loads(serialized)
    if not isinstance(result, dict):
        raise UnexpectedType(
            f"Object loaded from json is expected to be a dict, got a {type(result).__name__}\nObject: {result}"
        )
    return result
