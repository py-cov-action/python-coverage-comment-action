import dataclasses
import inspect
from typing import Any

from coverage_comment import log


class MissingEnvironmentVariable(Exception):
    pass


@dataclasses.dataclass(kw_only=True)
class Config:
    """This object defines the environment variables"""

    GITHUB_BASE_REF: str
    GITHUB_TOKEN: str = dataclasses.field(repr=False)
    GITHUB_REPOSITORY: str
    GITHUB_REF: str
    GITHUB_EVENT_NAME: str
    GITHUB_PR_RUN_ID: int
    BADGE_FILENAME: str = "python-coverage-comment-action-badge.json"
    COMMENT_ARTIFACT_NAME: str = "python-coverage-comment-action"
    COMMENT_FILENAME: str = "python-coverage-comment-action.txt"
    MINIMUM_GREEN: float = 100.0
    MINIMUM_ORANGE: float = 70.0
    MERGE_COVERAGE_FILES: bool = False
    TEMPLATE_PATH: str = "/var/default.md.j2"
    VERBOSE: bool = False

    # Clean methods
    @classmethod
    def clean_diff_cover_args(cls, value: str) -> list:
        return [e.strip() for e in value.split("\n") if e.strip()]

    @classmethod
    def clean_badge_enabled(cls, value: str) -> bool:
        return value.lower() in ("1", "true", "yes")

    @classmethod
    def clean_minimum_green(cls, value: str) -> float:
        return float(value)

    @classmethod
    def clean_minimum_orange(cls, value: str) -> float:
        return float(value)

    @classmethod
    def clean_github_pr_run_id(cls, value: str) -> int:
        return int(value)

    @classmethod
    def clean_merge_coverage_files(cls, value: str) -> bool:
        return value == "true"

    @classmethod
    def clean_verbose(cls, value: str) -> bool:
        return value == "true"

    @property
    def GITHUB_PR_NUMBER(self) -> int | None:
        # "refs/pull/2/merge"
        if "pull" in self.GITHUB_REF:
            return int(self.GITHUB_REF.split("/")[2])
        return None

    @property
    def GITHUB_BRANCH_NAME(self) -> str | None:
        # "refs/pull/2/merge"
        if self.GITHUB_REF.startswith("refs/heads/"):
            return self.GITHUB_REF.split("/")[-1]
        return None

    @classmethod
    def from_environ(cls, environ: dict[str, str]) -> "Config":
        possible_variables = [e for e in inspect.signature(cls).parameters]
        config: dict[str, Any] = {
            k: v for k, v in environ.items() if k in possible_variables
        }
        for key, value in list(config.items()):
            if func := getattr(cls, f"clean_{key.lower()}", None):
                config[key] = func(value)

        try:
            config = cls(**config)
        except TypeError:
            missing = {
                name
                for name, param in inspect.signature(cls).parameters.items()
                if param.default is inspect.Parameter.empty
            } - set(environ)
            raise MissingEnvironmentVariable(
                f" missing environment variable(s): {', '.join(missing)}"
            )

        log.debug(f"Settings: {config!r}")
        return config
