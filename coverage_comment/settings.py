import dataclasses
import inspect
import pathlib
from typing import Any


class MissingEnvironmentVariable(Exception):
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
    MINIMUM_GREEN: float = 100.0
    MINIMUM_ORANGE: float = 70.0
    MERGE_COVERAGE_FILES: bool = False
    VERBOSE: bool = False
    # Only for debugging, not exposed in the action:
    FORCE_WORKFLOW_RUN: bool = False

    # Clean methods
    @classmethod
    def clean_minimum_green(cls, value: str) -> float:
        return float(value)

    @classmethod
    def clean_minimum_orange(cls, value: str) -> float:
        return float(value)

    @classmethod
    def clean_github_pr_run_id(cls, value: str) -> int | None:
        return int(value) if value else None

    @classmethod
    def clean_merge_coverage_files(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_verbose(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_force_workflow_run(cls, value: str) -> bool:
        return str_to_bool(value)

    @classmethod
    def clean_comment_filename(cls, value: str) -> pathlib.Path:
        return path_below(value)

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
