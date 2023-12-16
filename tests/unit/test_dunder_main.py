from __future__ import annotations

import pytest

from coverage_comment import __main__


@pytest.mark.parametrize(
    "name, expected",
    [
        ("__main__", True),
        ("foo", False),
    ],
)
def test_main_call(mocker, name, expected):
    main = mocker.patch("coverage_comment.main.main")

    __main__.main_call(name)

    assert main.called is expected
