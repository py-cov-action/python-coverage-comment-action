from __future__ import annotations

import decimal

import pytest

from coverage_comment import badge


@pytest.mark.parametrize(
    "rate, expected",
    [
        (decimal.Decimal("10"), "red"),
        (decimal.Decimal("80"), "orange"),
        (decimal.Decimal("99"), "brightgreen"),
    ],
)
def test_get_badge_color(rate, expected):
    color = badge.get_badge_color(
        rate=rate,
        minimum_green=decimal.Decimal("90"),
        minimum_orange=decimal.Decimal("60"),
    )
    assert color == expected


@pytest.mark.parametrize(
    "delta, up_is_good, neutral_color, expected",
    [
        (decimal.Decimal("-5"), True, "lightgrey", "red"),
        (decimal.Decimal("5"), True, "lightgrey", "brightgreen"),
        (decimal.Decimal("-5"), False, "lightgrey", "brightgreen"),
        (decimal.Decimal("5"), False, "lightgrey", "red"),
        (decimal.Decimal("0"), False, "blue", "blue"),
        (decimal.Decimal("0"), False, "lightgrey", "lightgrey"),
        (decimal.Decimal("0"), True, "lightgrey", "lightgrey"),
    ],
)
def test_get_evolution_badge_color(delta, up_is_good, neutral_color, expected):
    color = badge.get_evolution_badge_color(
        delta=delta,
        up_is_good=up_is_good,
        neutral_color=neutral_color,
    )
    assert color == expected


def test_compute_badge_endpoint_data():
    badge_data = badge.compute_badge_endpoint_data(
        line_rate=decimal.Decimal("27.42"), color="red"
    )
    expected = """{"schemaVersion": 1, "label": "Coverage", "message": "27%", "color": "red"}"""
    assert badge_data == expected


def test_compute_badge_image(session):
    session.register(
        "GET", "https://img.shields.io/static/v1?label=Coverage&message=27%25&color=red"
    )(text="foo")

    badge_data = badge.compute_badge_image(
        line_rate=decimal.Decimal("27.42"), color="red", http_session=session
    )

    assert badge_data == "foo"


def test_get_static_badge_url():
    result = badge.get_static_badge_url(
        label="a-b", message="c_d e", color="green", format="svg"
    )

    assert result == "https://img.shields.io/badge/a--b-c__d%20e-green.svg"


@pytest.mark.parametrize(
    "label, message, color",
    [
        (
            "Label",
            "",
            "brightgreen",
        ),
        (
            "Label",
            "100% > 99%",
            "",
        ),
    ],
)
def test_get_static_badge_url__error(label, message, color):
    with pytest.raises(ValueError):
        badge.get_static_badge_url(label=label, message=message, color=color)


def test_get_endpoint_url():
    url = badge.get_endpoint_url(endpoint_url="https://foo")
    expected = "https://img.shields.io/endpoint?url=https://foo"

    assert url == expected


def test_get_dynamic_url():
    url = badge.get_dynamic_url(endpoint_url="https://foo")
    expected = "https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Ffoo"

    assert url == expected
