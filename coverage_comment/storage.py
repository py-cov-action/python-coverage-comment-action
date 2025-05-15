from __future__ import annotations

import contextlib
import pathlib

from coverage_comment import files, github_client, log, subprocess

GITHUB_ACTIONS_BOT_NAME = "github-actions"
# A discussion pointing at the email address of the github-actions bot user;
# https://github.community/t/github-actions-bot-email-address/17204/5
# To double-check, the bot's ID can be found at:
# https://api.github.com/users/github-actions[bot]
# The rule for creating the address can be found at:
# https://docs.github.com/en/account-and-profile/setting-up-and-managing-your-personal-account-on-github/managing-email-preferences/setting-your-commit-email-address#about-commit-email-addresses
GITHUB_ACTIONS_BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"

# Both Author and Committer identification are needed for git to let us commit
# (usually, both are derived from `git config user.{name|email}`)
COMMIT_ENVIRONMENT = {
    "GIT_AUTHOR_NAME": GITHUB_ACTIONS_BOT_NAME,
    "GIT_AUTHOR_EMAIL": GITHUB_ACTIONS_BOT_EMAIL,
    "GIT_COMMITTER_NAME": GITHUB_ACTIONS_BOT_NAME,
    "GIT_COMMITTER_EMAIL": GITHUB_ACTIONS_BOT_EMAIL,
}
GIT_COMMIT_MESSAGE = "Update coverage data"


@contextlib.contextmanager
def checked_out_branch(git: subprocess.Git, branch: str):
    # If we're not on a branch, `git branch --show-current` will print nothing
    # and still exit with 0.
    current_checkout = git.branch("--show-current").strip()
    is_on_a_branch = bool(current_checkout)
    if not is_on_a_branch:
        current_checkout = git.rev_parse("--short", "HEAD").strip()

    log.debug(f"Current checkout is {current_checkout}")

    log.debug("Resetting all changes")
    # Goodbye `.coverage` file.
    git.reset("--hard")

    try:
        git.fetch("origin", branch)
    except subprocess.SubProcessError:
        # Branch seems to no exist, OR fetch failed for a different reason.
        # Let's make sure:
        # 1/ Fetch again, but this time all the remote
        git.fetch("origin")
        # 2/ And check that our branch really doesn't exist
        try:
            git.rev_parse("--verify", f"origin/{branch}")
        except subprocess.SubProcessError:
            # Ok good, the branch really doesn't exist.
            pass
        else:
            # Ok, our branch exist, but we failed to fetch it. Let's raise.
            raise
        log.debug(f"Branch {branch} doesn't exist.")
        log.info(f"Creating branch {branch}")
        git.switch("--orphan", branch)
    else:
        log.debug(f"Branch {branch} exist.")
        git.switch(branch)

    try:
        yield
    finally:
        log.debug(f"Back to checkout of {current_checkout}")
        detach = ["--detach"] if not is_on_a_branch else []
        git.switch(*detach, current_checkout)


def commit_operations(
    operations: list[files.Operation],
    git: subprocess.Git,
    branch: str,
):
    """
    Store the given files.

    Parameters
    ----------
    operations : list[files.Operation]
        File operations to process
    git : subprocess.Git
        Git actor
    branch : str
        branch on which to store the files
    """
    with checked_out_branch(git=git, branch=branch):
        for op in operations:
            op.apply()
            git.add(str(op.path))

        try:
            git.diff("--staged", "--exit-code")
        except subprocess.GitError:
            pass  # All good, command returns 1 if there's diff, 0 otherwise
        else:
            log.info("No change detected, skipping.")
            return

        log.info("Saving coverage files")
        git.commit(
            "--message",
            GIT_COMMIT_MESSAGE,
            env=COMMIT_ENVIRONMENT,
        )
        git.push("origin", branch)

        log.info("Files saved")


def get_datafile_contents(
    github: github_client.GitHub,
    repository: str,
    branch: str,
) -> str | None:
    contents_path = github.repos(repository).contents(str(files.DATA_PATH))
    try:
        response = contents_path.get(
            ref=branch,
            # If we don't pass this header, the format of the answer will depend on
            # the size of the file. With the header, we're sure to get the raw content.
            headers={"Accept": "application/vnd.github.raw+json"},
        )
    except github_client.NotFound:
        return None

    return response


def get_raw_file_url(
    github_host: str,
    repository: str,
    branch: str,
    path: pathlib.Path,
    is_public: bool,
):
    if (not is_public) or (not github_host.endswith("github.com")):
        # If the repository is private or hosted on a github enterprise instance,
        # then the real links to raw.githubusercontents.com will be short-lived.
        # In this case, it's better to keep an URL that will  redirect to the correct URL just when asked.
        return f"{github_host}/{repository}/raw/{branch}/{path}"

    # Otherwise, we can access the file directly. (shields.io doesn't like the
    # github.com domain)
    return f"https://raw.githubusercontent.com/{repository}/{branch}/{path}"

    # Another way of accessing the URL would be
    # github.repos(repository).contents(str(path)).get(ref=branch).download_url
    # but this would only work if the file already exists when generating this URL,
    # and for private repos, it would create URLs that become inactive after a few
    # seconds.


def get_repo_file_url(
    github_host: str, repository: str, branch: str, path: str = "/"
) -> str:
    """
    Computes the GitHub Web UI URL for a given path:
    If the path is empty or ends with a slash, it will be interpreted as a folder,
    so the URL will point to the page listing files and displaying the README.
    Otherwise, the URL will point to the page displaying the file contents within
    the UI.
    Leading and trailing slashes in path are removed from the final URL.
    """
    # See test_get_repo_file_url for precise specifications
    path = "/" + path.lstrip("/")
    part = "tree" if path.endswith("/") else "blob"
    return f"{github_host}/{repository}/{part}/{branch}{path}".rstrip("/")


def get_html_report_url(github_host: str, repository: str, branch: str) -> str:
    readme_url = get_repo_file_url(
        github_host, repository=repository, branch=branch, path="/htmlcov/index.html"
    )
    if github_host.endswith("github.com"):
        return f"https://htmlpreview.github.io/?{readme_url}"
    return readme_url
