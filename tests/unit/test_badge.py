import pytest

from coverage_comment import badge


@pytest.mark.parametrize(
    "rate, expected",
    [
        (10, "red"),
        (80, "orange"),
        (99, "brightgreen"),
    ],
)
def test_get_badge_color(rate, expected):
    color = badge.get_badge_color(rate=rate, minimum_green=90, minimum_orange=60)
    assert color == expected


def test_compute_badge_endpoint_data():

    badge_data = badge.compute_badge_endpoint_data(line_rate=27.42, color="red")
    expected = """{"schemaVersion": 1, "label": "Coverage", "message": "27%", "color": "red"}"""
    assert badge_data == expected


def test_compute_badge_image(session):
    session.register(
        "GET", "https://img.shields.io/static/v1?label=Coverage&message=27%25&color=red"
    )(text="foo")

    badge_data = badge.compute_badge_image(
        line_rate=27.42, color="red", http_session=session
    )

    assert badge_data == "foo"


def test_get_endpoint_url():
    url = badge.get_endpoint_url(endpoint_url="https://foo")
    expected = "https://img.shields.io/endpoint?url=https://foo"

    assert url == expected


def test_get_dynamic_url():
    url = badge.get_dynamic_url(endpoint_url="https://foo")
    expected = "https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Ffoo"

    assert url == expected
