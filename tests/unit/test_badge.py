import pytest

from coverage_comment import badge


@pytest.mark.parametrize(
    "line_rate, badge_json",
    [
        (
            0.2,
            """{"schemaVersion": 1, "label": "Coverage", "message": "20%", "color": "red"}""",
        ),
        (
            0.8,
            """{"schemaVersion": 1, "label": "Coverage", "message": "80%", "color": "orange"}""",
        ),
        (
            1.0,
            """{"schemaVersion": 1, "label": "Coverage", "message": "100%", "color": "brightgreen"}""",
        ),
    ],
)
def test_compute_badge_json(line_rate, badge_json):

    result = badge.compute_badge_json(
        line_rate=line_rate, minimum_green=90, minimum_orange=50
    )

    assert result == badge_json


def test_parse_badge():
    badge_json = """{"schemaVersion": 1, "label": "Coverage", "message": "20%", "color": "red"}"""
    assert badge.parse_badge(badge_json) == 0.2


def test_get_badge_shield_url():
    url = "http://example.com"
    expected = "https://img.shields.io/endpoint?url=http://example.com"
    assert badge.get_badge_shield_url(json_url=url) == expected
