from __future__ import annotations

import pytest

from coverage_comment import __main__


@pytest.mark.parametrize(
    "name, expected",
    [
        ("__main__", [True]),
        ("foo", []),
    ],
)
def test_main_call(name, expected):
    called = []
    __main__.main_call(name, main_func=lambda: called.append(True))

    assert called == expected
