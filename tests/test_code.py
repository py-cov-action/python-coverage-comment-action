import pytest

from . import code


@pytest.mark.parametrize("arg, expected", [(None, "a")])
def test_code(arg, expected):
    assert code.code(arg) == expected
