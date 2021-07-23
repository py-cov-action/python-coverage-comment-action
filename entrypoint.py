#!/usr/bin/env python3

import dataclasses
import inspect
import os
import subprocess
import sys
import tempfile
from typing import List


def main():
    config = Config.from_environ(os.environ)

    comment = get_markdown_comment(config=config)
    post_comment(comment=comment, config=config)

    if config.badge_enabled:
        coverage_percent = get_coverage(config=config)
        upload_badge(coverage_percent=coverage_percent, config=config)


@dataclasses.dataclass
class Config:
    """This object defines the environment variables"""

    GITHUB_TOKEN: str
    COVERAGE_FILE: str = "coverage.xml"
    DIFF_COVER_ARGS: List[str] = dataclasses.field(default_factory=list)
    BADGE_ENABLED: bool = False

    # Clean methods
    @classmethod
    def clean_diff_cover_args(cls, value: str) -> list:
        return [e.strip() for e in value.split("\n")]

    @classmethod
    def clean_badge_enabled(cls, value: str) -> bool:
        return value.lower() in ("1", "true", "yes")

    @classmethod
    def from_environ(cls, environ):
        possible_variables = [e for e in inspect.signature(cls).parameters]
        config = {k: v for k, v in environ.items() if k in possible_variables}
        for key, value in list(config.items()):
            if func := getattr(cls, f"clean_{key.lower()}", None):
                config[key] = func(value)

        try:
            return cls(**config)
        except TypeError as exc:
            sys.exit(f"{exc} environment variable is mandatory")


def get_markdown_comment(config: Config) -> str:
    with tempfile.NamedTemporaryFile("r") as f:
        subprocess.check_call(
            ["diff-cover", "coverage.xml", "--markdown-report", f.name]
            + config.DIFF_COVER_ARGS
        )
        return f.read()


def post_comment(comment: str, config: Config) -> None:
    pass


def get_coverage(config: Config) -> int:
    pass


def upload_badge(coverage_percent: int, config: Config) -> None:
    pass


if __name__ == "__main__":
    main()
