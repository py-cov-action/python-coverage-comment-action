import pytest

from . import code


@pytest.mark.parametrize(
    "arg, expected",
    [
        (None, "a"),
        (True, "b"),
    ],
)
def test_code(arg, expected):
    assert code.code(arg) == expected
