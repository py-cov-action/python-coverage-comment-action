import json

SHIELD_URL = "https://img.shields.io/endpoint?url={url}"


def compute_badge(
    line_rate: float,
    minimum_green: float,  # 0.0 < x < 100.0
    minimum_orange: float,  # 0.0 < x < 100.0
) -> str:
    rate = int(line_rate * 100)

    if rate >= minimum_green:
        color = "brightgreen"
    elif rate >= minimum_orange:
        color = "orange"
    else:
        color = "red"

    badge = {
        "schemaVersion": 1,
        "label": "Coverage",
        "message": f"{rate}%",
        "color": color,
    }

    return json.dumps(badge)


def parse_badge(contents):
    return float(json.loads(contents)["message"][:-1]) / 100


def get_badge_shield_url(json_url) -> str:
    return SHIELD_URL.format(url=json_url)
