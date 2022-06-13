import json

from pybadges import badge as pybadge

SHIELD_URL = "https://img.shields.io/endpoint?url={url}"


def compute_badge_json(
    line_rate: float,
    minimum_green: float,  # 0.0 < x < 100.0
    minimum_orange: float,  # 0.0 < x < 100.0
) -> str:
    badge_data = get_badge(line_rate, minimum_green, minimum_orange)
    return json.dumps(badge_data)


def compute_badge_svg(
    line_rate: float,
    minimum_green: float,  # 0.0 < x < 100.0
    minimum_orange: float,  # 0.0 < x < 100.0
) -> str:
    badge_data = get_badge(line_rate, minimum_green, minimum_orange)
    return pybadge(
        left_text=badge_data["label"],
        right_text=badge_data["message"],
        right_color=badge_data["color"],
    )


def get_badge(
    line_rate: float,
    minimum_green: float,  # 0.0 < x < 100.0
    minimum_orange: float,  # 0.0 < x < 100.0
):
    rate = int(line_rate * 100)

    if rate >= minimum_green:
        color = "brightgreen"
    elif rate >= minimum_orange:
        color = "orange"
    else:
        color = "red"

    badge_data = {
        "schemaVersion": 1,
        "label": "Coverage",
        "message": f"{rate}%",
        "color": color,
    }
    return badge_data


def parse_badge(contents):
    return float(json.loads(contents)["message"][:-1]) / 100


def get_badge_shield_url(json_url) -> str:
    return SHIELD_URL.format(url=json_url)
