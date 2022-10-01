import csv
import pathlib

import end_to_end_tests_repo
import pytest


def load_csv():
    file = pathlib.Path(__file__).parent / "cases.csv"
    return list(csv.reader(file.read_text().splitlines()))


@pytest.mark.parametrize("a, b, c, d, expected", load_csv())
def test_f(a, b, c, d, expected):
    assert end_to_end_tests_repo.f(a=a, b=b, c=c, d=d) == expected
