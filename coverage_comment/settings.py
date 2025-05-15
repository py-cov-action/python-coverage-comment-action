from __future__ import annotations

import dataclasses
import decimal
import inspect
import pathlib
from collections.abc import MutableMapping
from typing import Any

from coverage_comment import log


class MissingEnvironmentVariable(Exception):
    pass


class InvalidAnnotationType(Exception):
    pass


def path_below(path_str: str | pathlib.Path) -> pathlib.Path:
    try:
        return pathlib.Path(path_str).resolve().relative_to(pathlib.Path.cwd())
    except ValueError as exc:
        raise ValueError(
            "Path needs to be relative and below the current directory"
        ) from exc


def str_to_bool(value: str) -> bool:
    return value.lower() in ("1", "true", "yes")


@dataclasses.dataclass(kw_only=True)
class Config:
    """This object defines the environment variables"""

    # A branch name, not a fully-formed ref. For example, `main`.
    GITHUB_BASE_REF: str
    GITHUB_BASE_URL: str = "https://api.github.com"
    GITHUB_TOKEN: str = dataclasses.field(repr=False)
    GITHUB_REPOSITORY: str
    # > The ref given is fully-formed, meaning that for branches the format is
    # > `refs/heads/<branch_name>`, for pull requests it is
    # > `refs/pull/<pr_number>/merge`, and for tags it is `refs/tags/<tag_name>`.
    # > For example, `refs/heads/feature-branch-1`.
    # (from https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables )
    GITHUB_REF: str
    GITHUB_EVENT_NAME: str
    GITHUB_EVENT_PATH: pathlib.Path | None = None
    GITHUB_PR_RUN_ID: int | None
    GITHUB_STEP_SUMMARY: pathlib.Path
    COMMENT_TEMPLATE: str | None = None
    COVERAGE_DATA_BRANCH: str = "python-coverage-comment-action-data"
    COVERAGE_PATH: pathlib.Path = pathlib.Path(".")
    COMMENT_ARTIFACT_NAME: str = "python-coverage-comment-action"
    COMMENT_FILENAME: pathlib.Path = pathlib.Path("python-coverage-comment-action.txt")
    SUBPROJECT_ID: str | None = None
    GITHUB_OUTPUT: pathlib.Path | None = None
    MINIMUM_GREEN: decimal.Decimal = decimal.Decimal("100")
    MINIMUM_ORANGE: decimal.Decimal = decimal.Decimal("70")
    MERGE_COVERAGE_FILES: bool = False
    ANNOTATE_MISSING_LINES: bool = False
    ANNOTATION_TYPE: str = "warning"
    MAX_FILES_IN_COMMENT: int = 25
    VERBOSE: bool = False
    # Only for debugging, not exposed in the action:
    FORCE_WORKFLOW_RUN: bool = False

    # Clean methods
    @classmethod
    def clean_minimum_green(cls, value: str) -> decimal.Decimal:
        return decimal.Decimal(value)

    @classmethod
    def clean_minimum_orange(cls, value: str) -> decimal.Decimal:
        return decimal.Decimal(value)

    @classmethod
    def clean_github_pr_run_id(cls, value: str) -> int | None:
        return int(value) if value else None

    @classmethod
    def clean_github_step_summary(cls, value: str) -> pathlib.Path:
        return pathlib.Path(value)

    @classmethod
    def clean_merge_coverage_files(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_annotate_missing_lines(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_annotation_type(cls, value: str) -> str:
        if value not in {"notice", "warning", "error"}:
            raise InvalidAnnotationType(
                f"The annotation type {value} is not valid. Please choose from notice, warning or error"
            )
        return value

    @classmethod
    def clean_verbose(cls, value: str) -> bool:
        if str_to_bool(value):
            log.info(
                "VERBOSE setting is deprecated. For increased debug output, see https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/enabling-debug-logging"
            )
        return False

    @classmethod
    def clean_force_workflow_run(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_comment_filename(cls, value: str) -> pathlib.Path:
        return path_below(value)

    @classmethod
    def clean_coverage_path(cls, value: str) -> pathlib.Path:
        return path_below(value)

    @classmethod
    def clean_github_output(cls, value: str) -> pathlib.Path:
        return pathlib.Path(value)

    @property
    def GITHUB_PR_NUMBER(self) -> int | None:
        # "refs/pull/2/merge"
        if self.GITHUB_REF.startswith("refs/pull"):
            return int(self.GITHUB_REF.split("/")[2])
        return None

    @property
    def GITHUB_BRANCH_NAME(self) -> str | None:
        # "refs/heads/my_branch_name"
        if self.GITHUB_REF.startswith("refs/heads"):
            return self.GITHUB_REF.split("/", 2)[2]
        return None

    @property
    def FINAL_COMMENT_FILENAME(self):
        filename = self.COMMENT_FILENAME
        if self.SUBPROJECT_ID:
            new_name = f"{filename.stem}-{self.SUBPROJECT_ID}{filename.suffix}"
            return filename.parent / new_name
        return filename

    @property
    def FINAL_COVERAGE_DATA_BRANCH(self):
        return self.COVERAGE_DATA_BRANCH + (
            f"-{self.SUBPROJECT_ID}" if self.SUBPROJECT_ID else ""
        )

    # We need to type environ as a MutableMapping because that's what
    # os.environ is, and just saying `dict[str, str]` is not enough to make
    # mypy happy
    @classmethod
    def from_environ(cls, environ: MutableMapping[str, str]) -> Config:
        possible_variables = [e for e in inspect.signature(cls).parameters]
        config: dict[str, Any] = {
            k: v for k, v in environ.items() if k in possible_variables
        }
        for key, value in list(config.items()):
            if func := getattr(cls, f"clean_{key.lower()}", None):
                try:
                    config[key] = func(value)
                except ValueError as exc:
                    raise ValueError(f"{key}: {exc!s}") from exc

        try:
            config_obj = cls(**config)
        except TypeError:
            missing = {
                name
                for name, param in inspect.signature(cls).parameters.items()
                if param.default is inspect.Parameter.empty
            } - set(environ)
            raise MissingEnvironmentVariable(
                f" missing environment variable(s): {', '.join(missing)}"
            )
        return config_obj
