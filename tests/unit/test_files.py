import pathlib

import pytest

from coverage_comment import files


@pytest.mark.parametrize(
    "input, output",
    [
        (1, 100),
        (0.99999, 99.99),
        (0.05, 5.0),
        (0.051, 5.1),
        (0.0512, 5.12),
        (0.05121, 5.12),
        (0.05129, 5.12),
    ],
)
def test_get_percentage(input, output):
    # Yeah, I didn't foresee that we would need so many samples to make
    # sure the function works, but floats are hard. It all comes from:
    # >>> 5.1 * 100
    # 509.99999999999994
    assert files.get_percentage(input) == output


def test_compute_files(session):

    session.register(
        "GET", "https://img.shields.io/static/v1?label=Coverage&message=12%25&color=red"
    )(text="foo")

    result = files.compute_files(
        line_rate=0.1234,
        minimum_green=25,
        minimum_orange=70,
        http_session=session,
    )
    expected = [
        files.FileWithPath(
            path=pathlib.Path("endpoint.json"),
            contents='{"schemaVersion": 1, "label": "Coverage", "message": "12%", "color": "red"}',
        ),
        files.FileWithPath(
            path=pathlib.Path("data.json"), contents='{"coverage": 12.34}'
        ),
        files.FileWithPath(path=pathlib.Path("badge.svg"), contents="foo"),
    ]
    assert result == expected


def test_compute_datafile():
    assert files.compute_datafile(line_rate=12.34) == """{"coverage": 12.34}"""


def test_parse_datafile():
    assert files.parse_datafile(contents="""{"coverage": 12.34}""") == 0.1234


def test_get_urls():
    def getter(path):
        return f"https://{path}"

    urls = files.get_urls(url_getter=getter)

    assert urls == {
        "direct": "https://badge.svg",
        "dynamic": "https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fendpoint.json",
        "endpoint": "https://img.shields.io/endpoint?url=https://endpoint.json",
    }
