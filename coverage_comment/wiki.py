import functools
import pathlib
import tempfile
from typing import Any

import httpx

from coverage_comment import log, subprocess

WIKI_FILE_URL = "https://raw.githubusercontent.com/wiki/{repository}/{filename}"
GIT_CONFIG_EMAIL = "python-coverage-comment-action"
GIT_CONFIG_NAME = "python-coverage-comment-action"
GIT_COMMIT_MESSAGE = "Update badge"


class GitError(Exception):
    pass


class Git:
    def __init__(self, cwd):
        self.cwd = cwd

    def _git(self, *args, **kwargs):
        try:
            return subprocess.run(
                "git",
                *args,
                cwd=self.cwd,
                **kwargs,
            )
        except subprocess.SubProcessError as exc:
            raise GitError from exc

    def __getattr__(self, name: str) -> Any:
        return functools.partial(self._git, name)


def upload_file(
    github_token: str,
    repository: str,
    filename: str,
    contents: str,
    git: Git | None = None,
):
    with tempfile.TemporaryDirectory() as dir_path:
        dir = pathlib.Path(dir_path)
        git = Git(cwd=dir) if git is None else git

        git.clone(
            f"https://x-access-token:{github_token}@github.com/{repository}.wiki.git",
            ".",
        )
        (dir / filename).write_text(contents)
        git.add(filename)

        try:
            git.diff("--staged", "--exit-code")
        except GitError:
            pass  # All good, command returns 1 if there's diff, 0 otherwise
        else:
            log.info("No change detected, skipping.")
            return

        git.config("user.email", GIT_CONFIG_EMAIL)
        git.config("user.name", GIT_CONFIG_NAME)

        git.commit("-m", GIT_COMMIT_MESSAGE)

        try:
            git.push("-u", "origin")
        except GitError as exc:
            if "remote error: access denied or repository not exported" in str(exc):
                log.error(
                    "Wiki seems not to be activated for this project. Please activate the "
                    "wiki and create a single page. You may disable it afterwards."
                )

            log.error("Push error")
            raise


def get_file_contents(repository: str, filename: str) -> str | None:
    try:
        response = httpx.get(
            get_wiki_file_url(repository=repository, filename=filename)
        )
        return response.text
    except Exception:
        log.warning("Previous coverage results not found, cannot report on evolution.")
        log.debug("Exception while getting previous coverage data", exc_info=True)
        return None


def get_wiki_file_url(repository: str, filename: str) -> str:
    return WIKI_FILE_URL.format(repository=repository, filename=filename)
