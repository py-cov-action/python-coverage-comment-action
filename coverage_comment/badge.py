"""
This module should contain only the things relevant to the badge being computed
by shields.io
"""

import json
import urllib.parse

import httpx


def get_badge_color(
    # All float values are between 0 and 100 with 2 decimal places
    rate: float,
    minimum_green: float,
    minimum_orange: float,
) -> str:
    if rate >= minimum_green:
        return "brightgreen"
    elif rate >= minimum_orange:
        return "orange"
    else:
        return "red"


def compute_badge_endpoint_data(
    line_rate: float,
    color: str,
) -> str:

    badge = {
        "schemaVersion": 1,
        "label": "Coverage",
        "message": f"{int(line_rate)}%",
        "color": color,
    }

    return json.dumps(badge)


def compute_badge_image(
    line_rate: float, color: str, http_session: httpx.Client
) -> str:
    return http_session.get(
        "https://img.shields.io/static/v1?"
        + urllib.parse.urlencode(
            {
                "label": "Coverage",
                "message": f"{int(line_rate)}%",
                "color": color,
            }
        )
    ).text


def get_endpoint_url(endpoint_url: str) -> str:
    return f"https://img.shields.io/endpoint?url={endpoint_url}"


def get_dynamic_url(endpoint_url: str) -> str:
    return "https://img.shields.io/badge/dynamic/json?" + urllib.parse.urlencode(
        {
            "color": "brightgreen",
            "label": "coverage",
            "query": "$.message",
            "url": endpoint_url,
        }
    )
