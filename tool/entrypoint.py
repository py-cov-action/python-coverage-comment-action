#!/usr/bin/env python3

import dataclasses
import inspect
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import List, Optional

import ghapi
import jinja2
import xmltodict

MARKER = """<!-- This comment was produced by coverage-comment-action -->"""
BADGE_FILENAME = "coverage-comment-badge.json"
MINIMUM_GREEN = 100
MINIMUM_ORANGE = 70


def main():
    config = Config.from_environ(os.environ)
    coverage_info = get_coverage_info(config=config)
    diff_coverage_info = get_diff_coverage_info(config=config)
    previous_coverage_rate = get_previous_coverage_rate(config=config)

    comment = get_markdown_comment(
        coverage_info=coverage_info,
        diff_coverage_info=diff_coverage_info,
        previous_coverage_rate=previous_coverage_rate,
        config=config,
    )
    post_comment(comment=comment, config=config)

    if config.BADGE_ENABLED:
        badge = compute_badge(coverage_info=coverage_info)
        upload_badge(badge=badge, config=config)


@dataclasses.dataclass
class Config:
    """This object defines the environment variables"""

    GITHUB_BASE_REF: str
    GITHUB_TOKEN: str
    GITHUB_OWNER: str
    GITHUB_REPO: str
    GITHUB_PR_NUMBER: str
    COVERAGE_FILE: str = "coverage.xml"
    COMMENT_TEMPLATE: Optional[str] = None
    DIFF_COVER_ARGS: List[str] = dataclasses.field(default_factory=list)
    BADGE_ENABLED: bool = True

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


def get_coverage_info(config: Config) -> dict:
    def convert(tuple_values):
        result = []
        for key, value in tuple_values:
            result.append(
                (
                    key,
                    {
                        "@timestamp": int,
                        "@lines-valid": int,
                        "@lines-covered": int,
                        "@line-rate": float,
                        "@branches-valid": int,
                        "@branches-covered": int,
                        "@branch-rate": float,
                        "@complexity": int,
                        "@hits": int,
                        "@branch": lambda x: x == "true",
                    }.get(key, lambda x: x)(value),
                )
            )
        return dict(result)

    return json.loads(
        json.dumps(xmltodict.parse(pathlib.Path(config.COVERAGE_FILE).read_text())),
        object_pairs_hook=convert,
    )["coverage"]


def get_diff_coverage_info(config: Config) -> dict:
    with tempfile.NamedTemporaryFile("r") as f:
        subprocess.check_call(
            [
                "diff-cover",
                config.COVERAGE_FILE,
                f"--compare-branch=origin/{config.GITHUB_BASE_REF}",
                f"--json-report={f.name}",
                "--quiet",
            ]
            + config.DIFF_COVER_ARGS
        )
        return json.loads(f.read())


def get_markdown_comment(
    coverage_info: dict,
    diff_coverage_info: dict,
    previous_coverage_rate: Optional[float],
    config: Config,
):
    env = jinja2.Environment()
    template = (
        config.COMMENT_TEMPLATE or pathlib.Path("/tool/default.md.j2").read_text()
    )
    previous_coverage = previous_coverage_rate * 100 if previous_coverage_rate else None
    coverage = coverage_info["@line-rate"] * 100
    branch_coverage = (
        coverage["@branch-rate"] * 100 if coverage.get("@branch-rate") else None
    )
    diff_coverage = diff_coverage_info["total_percent_covered"]
    file_info = {
        file: {"diff_coverage": stats.percent_covered}
        for file, stats in diff_coverage["src_stats"].items()
    }
    return env.from_string(template).render(
        previous_coverage=previous_coverage,
        coverage=coverage,
        branch_coverage=branch_coverage,
        diff_coverage=diff_coverage,
        file_info=file_info,
        marker=MARKER,
    )


def post_comment(body: str, config: Config) -> None:
    api = ghapi.GhApi(
        owner=config.GITHUB_OWNER,
        repo=config.GITHUB_REPO,
        jwt_token=config.GITHUB_TOKEN,
    )
    me = api.users.get_authenticated()
    for comment in api.issues.list_comments(issue_number=config.GITHUB_PR_NUMBER):
        if comment.user.login == me.login and MARKER in comment.body:
            api.issues.update_comment(comment_id=comment.id, body=body)
    else:
        api.issues.create_comment(issue_number=config.GITHUB_PR_NUMBER, body=body)


def compute_badge(coverage_info: dict) -> str:
    rate = int(coverage_info["@line-rate"] * 100)

    if rate >= MINIMUM_GREEN:
        color = "green"
    elif rate >= MINIMUM_ORANGE:
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


def get_previous_coverage_rate(config: Config) -> Optional[float]:
    return 0.4242


def upload_badge(badge: str, config: Config) -> None:
    owner_repo = f"{config.GITHUB_OWNER}/{config.GITHUB_REPO}"
    subprocess.run(
        ["./add-to-wiki.sh", owner_repo, BADGE_FILENAME, "Update badge"],
        input=badge,
        text=True,
        check=True,
    )


if __name__ == "__main__":
    main()
