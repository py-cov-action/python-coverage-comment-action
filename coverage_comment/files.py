"""
This module contains info pertaining to the files we intend to save,
independently from storage specifics (storage.py)
"""
import dataclasses
import decimal
import json
import pathlib
from collections.abc import Callable
from typing import TypedDict

import httpx

from coverage_comment import badge

ENDPOINT_PATH = pathlib.Path("endpoint.json")
DATA_PATH = pathlib.Path("data.json")
BADGE_PATH = pathlib.Path("badge.svg")


@dataclasses.dataclass
class FileWithPath:
    path: pathlib.Path
    contents: str


def compute_files(
    line_rate: decimal.Decimal,
    minimum_green: decimal.Decimal,
    minimum_orange: decimal.Decimal,
    http_session: httpx.Client,
) -> list[FileWithPath]:
    line_rate *= decimal.Decimal("100")
    color = badge.get_badge_color(
        rate=line_rate,
        minimum_green=minimum_green,
        minimum_orange=minimum_orange,
    )
    return [
        FileWithPath(
            path=ENDPOINT_PATH,
            contents=badge.compute_badge_endpoint_data(
                line_rate=line_rate, color=color
            ),
        ),
        FileWithPath(
            path=DATA_PATH,
            contents=compute_datafile(line_rate=line_rate),
        ),
        FileWithPath(
            path=BADGE_PATH,
            contents=badge.compute_badge_image(
                line_rate=line_rate, color=color, http_session=http_session
            ),
        ),
    ]


def compute_datafile(line_rate: decimal.Decimal) -> str:
    return json.dumps({"coverage": float(line_rate)})


def parse_datafile(contents) -> decimal.Decimal:
    return decimal.Decimal(str(json.loads(contents)["coverage"])) / decimal.Decimal(
        "100"
    )


class ImageURLs(TypedDict):
    direct: str
    endpoint: str
    dynamic: str


def get_urls(url_getter: Callable) -> ImageURLs:
    return {
        "direct": url_getter(path=BADGE_PATH),
        "endpoint": badge.get_endpoint_url(endpoint_url=url_getter(path=ENDPOINT_PATH)),
        "dynamic": badge.get_dynamic_url(endpoint_url=url_getter(path=ENDPOINT_PATH)),
    }
