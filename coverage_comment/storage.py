import base64
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
INITIAL_GIT_COMMIT_MESSAGE = "Initialize python-coverage-comment-action special branch"
GIT_COMMIT_MESSAGE = "Update badge"


def initialize_branch(
    git: subprocess.Git,
    branch: str,
    initial_file: files.FileWithPath,
):

    log.info(f"Creating branch {branch}")
    git.checkout("--orphan", branch)
    git.reset("--hard")

    initial_file.path.write_text(initial_file.contents)
    git.add(str(initial_file.path))
    git.commit(
        "--message",
        INITIAL_GIT_COMMIT_MESSAGE,
        env=COMMIT_ENVIRONMENT,
    )


@contextlib.contextmanager
def on_coverage_branch(git: subprocess.Git, branch: str):
    try:
        current_checkout = git.branch("--show-current").strip()
    except subprocess.SubProcessError:
        current_checkout = git.rev_parse("--short", "HEAD").strip()

    log.debug(f"Current checkout is {current_checkout}")

    git.fetch()

    branch_existed = True
    try:
        git.checkout(branch)
        log.debug(f"Branch {branch} exist.")
    except subprocess.SubProcessError:
        log.debug(f"Branch {branch} doesn't exist.")
        branch_existed = False

    try:
        yield branch_existed
    finally:
        log.debug(f"Back to checkout of {current_checkout}")
        git.checkout(current_checkout)


def upload_files(
    files: list[files.FileWithPath],
    git: subprocess.Git,
    branch: str,
    initial_file: files.FileWithPath,
):
    """
    Store the given files.

    Parameters
    ----------
    files : list[files.FileWithPath]
        Files to store
    git : subprocess.Git
        Git actor
    branch : str
        branch on which to store the files
    initial_file : files.FileWithPath
        In case the branch didn't exist, initialize it with this initial file.
    """
    with on_coverage_branch(git=git, branch=branch) as branch_existed:
        if not branch_existed:
            initialize_branch(
                git=git,
                branch=branch,
                initial_file=initial_file,
            )

        for file in files:
            file.path.write_text(file.contents)
            git.add(str(file.path))

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
        response = contents_path.get(ref=branch)
    except github_client.NotFound:
        return None

    return base64.b64decode(response.content).decode()


def get_file_url(
    repository: str,
    branch: str,
    path: pathlib.Path,
    is_public: bool,
):
    if not is_public:
        # If the repository is private, then the real links to raw.githubusercontents.com
        # will be short-lived. In this case, it's better to keep an URL that will
        # redirect to the correct URL just when asked.
        return f"https://github.com/{repository}/raw/{branch}/{path}"

    # Otherwise, we can access the file directly. (shields.io doesn't like the
    # github.com domain)
    return f"https://raw.githubusercontent.com/{repository}/{branch}/{path}"

    # Another way of accessing the URL would be
    # github.repos(repository).contents(str(path)).get(ref=branch).download_url
    # but this would only work if the file already exists when generating this URL,
    # and for private repos, it would create URLs that become inactive after a few
    # seconds.


def get_readme_url(repository: str, branch: str) -> str:
    return f"https://github.com/{repository}/tree/{branch}"
