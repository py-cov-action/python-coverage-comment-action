"""
This module contains info pertaining to the files we intend to save,
independently from storage specifics (storage.py)
"""
import dataclasses
import decimal
import json
import pathlib
import shutil
from collections.abc import Callable
from typing import Protocol, TypedDict

import httpx

from coverage_comment import badge, coverage, log

ENDPOINT_PATH = pathlib.Path("endpoint.json")
DATA_PATH = pathlib.Path("data.json")
BADGE_PATH = pathlib.Path("badge.svg")


class Operation(Protocol):
    path: pathlib.Path

    def apply(self):
        ...


@dataclasses.dataclass
class WriteFile:
    path: pathlib.Path
    contents: str

    def apply(self):
        preview_len = 50
        ellipsis = "..." if len(self.contents) > preview_len else ""
        log.debug(f"Writing file {self.path} ({self.contents[:preview_len]}{ellipsis})")
        self.path.write_text(self.contents)


@dataclasses.dataclass
class ReplaceDir:
    """
    Deletes the dir at `path`, then copies the dir from source to destination
    """

    source: pathlib.Path
    path: pathlib.Path

    def apply(self):
        if self.path.exists():
            log.debug(f"Deleting {self.path}")
            shutil.rmtree(self.path)
        log.debug(f"Moving {self.source} to {self.path}")
        shutil.move(self.source, self.path)


def compute_files(
    line_rate: decimal.Decimal,
    minimum_green: decimal.Decimal,
    minimum_orange: decimal.Decimal,
    http_session: httpx.Client,
) -> list[Operation]:
    line_rate *= decimal.Decimal("100")
    color = badge.get_badge_color(
        rate=line_rate,
        minimum_green=minimum_green,
        minimum_orange=minimum_orange,
    )
    return [
        WriteFile(
            path=ENDPOINT_PATH,
            contents=badge.compute_badge_endpoint_data(
                line_rate=line_rate, color=color
            ),
        ),
        WriteFile(
            path=DATA_PATH,
            contents=compute_datafile(line_rate=line_rate),
        ),
        WriteFile(
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


def get_coverage_html_files() -> FileWithPath:
    coverage.generate_coverage_html_files()
    path = pathlib.Path("htmlcov")
    # Coverage will create a .gitignore if the htmlcov dir didn't exist before,
    # so we may or may not have one.
    (path / ".gitignore").unlink(missing_ok=True)
    return FileWithPath(path=path, contents=None)
