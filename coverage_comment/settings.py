import dataclasses
import decimal
import inspect
import pathlib
from typing import Any

from coverage_comment import log


class MissingEnvironmentVariable(Exception):
    pass


class InvalidAnnotationType(Exception):
    pass


def path_below(path_str: str) -> pathlib.Path:
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

    GITHUB_BASE_REF: str
    GITHUB_TOKEN: str = dataclasses.field(repr=False)
    GITHUB_REPOSITORY: str
    GITHUB_REF: str
    GITHUB_EVENT_NAME: str
    GITHUB_PR_RUN_ID: int | None
    COMMENT_TEMPLATE: str | None = None
    COVERAGE_DATA_BRANCH: str = "python-coverage-comment-action-data"
    COMMENT_ARTIFACT_NAME: str = "python-coverage-comment-action"
    COMMENT_FILENAME: pathlib.Path = pathlib.Path("python-coverage-comment-action.txt")
    GITHUB_OUTPUT: pathlib.Path | None = None
    MINIMUM_GREEN: decimal.Decimal = decimal.Decimal("100")
    MINIMUM_ORANGE: decimal.Decimal = decimal.Decimal("70")
    MERGE_COVERAGE_FILES: bool = False
    ANNOTATE_MISSING_LINES: bool = False
    ANNOTATION_TYPE: str = "warning"
    COV_DIFF_TO_ORIGIN: bool = False
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
    def clean_github_output(cls, value: str) -> pathlib.Path:
        return pathlib.Path(value)

    @property
    def GITHUB_PR_NUMBER(self) -> int | None:
        # "refs/pull/2/merge"
        if "pull" in self.GITHUB_REF:
            return int(self.GITHUB_REF.split("/")[2])
        return None

    @classmethod
    def from_environ(cls, environ: dict[str, str]) -> "Config":
        possible_variables = [e for e in inspect.signature(cls).parameters]
        config: dict[str, Any] = {
            k: v for k, v in environ.items() if k in possible_variables
        }
        for key, value in list(config.items()):
            if func := getattr(cls, f"clean_{key.lower()}", None):
                try:
                    config[key] = func(value)
                except ValueError as exc:
                    raise ValueError(f"{key}: {str(exc)}") from exc

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
