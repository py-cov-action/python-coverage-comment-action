import pathlib
import tempfile

import httpx

from coverage_comment import log, subprocess

WIKI_FILE_URL = "https://raw.githubusercontent.com/wiki/{repository}/{filename}"
GIT_CONFIG_EMAIL = "python-coverage-comment-action"
GIT_CONFIG_NAME = "python-coverage-comment-action"
GIT_COMMIT_MESSAGE = "Update badge"


def upload_file(
    github_token: str,
    repository: str,
    filename: pathlib.Path,
    contents: str,
    git: subprocess.Git,
):
    with tempfile.TemporaryDirectory() as dir_path:
        dir = pathlib.Path(dir_path)
        git.cwd = dir

        git.clone(
            f"https://x-access-token:{github_token}@github.com/{repository}.wiki.git",
            ".",
        )
        (dir / filename).write_text(contents)
        git.add(str(filename))

        try:
            git.diff("--staged", "--exit-code")
        except subprocess.GitError:
            pass  # All good, command returns 1 if there's diff, 0 otherwise
        else:
            log.info("No change detected, skipping.")
            return

        git.config("user.email", GIT_CONFIG_EMAIL)
        git.config("user.name", GIT_CONFIG_NAME)

        git.commit("-m", GIT_COMMIT_MESSAGE)

        try:
            git.push("-u", "origin")
        except subprocess.GitError as exc:
            if "remote error: access denied or repository not exported" in str(exc):
                log.error(
                    "Wiki seems not to be initialized for this project. Please activate the "
                    "wiki and create a single page. You may disable it afterwards."
                )

            log.error("Push error")
            raise


def get_file_contents(
    session: httpx.Client,
    repository: str,
    filename: pathlib.Path,
) -> str | None:
    try:
        response = session.get(
            get_wiki_file_url(repository=repository, filename=filename)
        )
        response.raise_for_status()
        return response.text
    except httpx.HTTPError:
        log.warning("Previous coverage results not found, cannot report on evolution.")
        log.debug("Exception while getting previous coverage data", exc_info=True)
        return None


def get_wiki_file_url(repository: str, filename: pathlib.Path) -> str:
    return WIKI_FILE_URL.format(repository=repository, filename=filename)
