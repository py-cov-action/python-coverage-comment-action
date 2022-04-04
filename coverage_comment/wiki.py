import contextlib
import pathlib
import tempfile

import httpx

from coverage_comment import log, subprocess

WIKI_FILE_URL = "https://raw.githubusercontent.com/wiki/{repository}/{filename}"
GIT_CONFIG_EMAIL = "python-coverage-comment-action"
GIT_CONFIG_NAME = "python-coverage-comment-action"
GIT_COMMIT_MESSAGE = "Update badge"


@contextlib.contextmanager
def cloned_wiki(
    repository: str,
    git: subprocess.Git,
    github_token: str,
):
    try:
        with tempfile.TemporaryDirectory() as dir_path:
            dir = pathlib.Path(dir_path)
            git.cwd = dir

            git.clone(
                f"https://x-access-token:{github_token}@github.com/{repository}.wiki.git",
                ".",
            )

            yield dir
    except Exception as exc:
        log.debug("Unhandled error occurred when cloning wiki.", exc_info=True)
        raise exc


def upload_file(
    github_token: str,
    repository: str,
    filename: pathlib.Path,
    contents: str,
    git: subprocess.Git,
):
    with cloned_wiki(repository, git, github_token) as wiki_dir:
        (wiki_dir / filename).write_text(contents)
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
    git: subprocess.Git | None = None,
    github_token: str | None = None,
) -> str | None:
    try:
        response = session.get(
            get_wiki_file_url(repository=repository, filename=filename)
        )
        response.raise_for_status()
        return response.text
    except httpx.HTTPError:
        # One possible reason is that the repository (and hence wiki) is private,
        # requiring us to clone the repo and get file contents that way
        if git and github_token:
            log.debug(
                "Exception while getting previous coverage data, attempting to download "
                "the file directly from the git repository (assuming the wiki is private)."
            )
            with cloned_wiki(repository, git, github_token) as wiki_dir:
                try:
                    return (wiki_dir / filename).read_text()
                except FileNotFoundError:
                    log.warning("File not found in the wiki's git repository.")

        log.warning("Previous coverage results not found, cannot report on evolution.")
        log.debug("Exception while getting previous coverage data", exc_info=True)
        return None


def get_wiki_file_url(repository: str, filename: pathlib.Path) -> str:
    return WIKI_FILE_URL.format(repository=repository, filename=filename)
