import io
import json
import pathlib
import zipfile
from typing import Any

from coverage_comment import github_client, log

GITHUB_ACTIONS_LOGIN = "github-actions[bot]"


class CannotDeterminePR(Exception):
    pass


class CannotPostComment(Exception):
    pass


class NoArtifact(Exception):
    pass


def get_api(token: str) -> github_client.GitHub:
    return github_client.GitHub(access_token=token)


def is_default_branch(
    github: github_client.GitHub, repository: str, branch: str
) -> bool:
    default_branch = github.repos(repository).get().default_branch
    return f"refs/heads/{default_branch}" == branch


def download_artifact(
    github: github_client.GitHub,
    repository: str,
    artifact_name: str,
    run_id: int,
    filename: pathlib.Path,
) -> str:
    repo_path = github.repos(repository)
    artifacts = repo_path.actions.runs(run_id).artifacts.get().artifacts
    try:
        artifact = next(
            iter(artifact for artifact in artifacts if artifact.name == artifact_name),
        )
    except StopIteration:
        raise NoArtifact(
            f"Not artifact found with name {artifact_name} in run {run_id}"
        )
    zip_bytes = io.BytesIO(repo_path.actions.artifacts(artifact.id).zip.get())
    zipf = zipfile.ZipFile(zip_bytes)
    return zipf.open(str(filename), "r").read().decode("utf-8")


def get_pr_number_from_workflow_run(
    github: github_client.GitHub, repository: str, run_id: int
) -> int:

    # It's quite horrendous to access the PR number from a workflow run,
    # especially when it's not the "pull_request" workflow run itself but a
    # "workflow_run" workflow run that runs after the "pull_request" workflow
    # run.
    #
    # 1. We need the user to give us access to the "pull_request" workflow run
    #    id. That why we request then to use
    #    GITHUB_PR_RUN_ID: ${{ github.event.workflow_run.id }}
    # 2. From that run, we get the corresponding branch, and the owner of the branch
    # 3. We list PRs that have that branch as head branch. There should be only one.

    repo_path = github.repos(repository)
    run = repo_path.actions.runs(run_id).get()
    branch = run.head_branch
    login = run.head_repository.owner.login
    prs = [pr.number for pr in repo_path.pulls.get(head=f"{login}:{branch}")]
    if len(prs) != 1:
        # 0 would be a problem, but >1 would also.
        raise CannotDeterminePR(f"Found 0 or more than 1 PRs: {prs!r}")
    return prs[0]


def get_my_login(github: github_client.GitHub):
    try:
        response = github.user.get()
    except github_client.ApiError as exc:
        if exc.response.status_code == 403:
            # The GitHub actions user cannot access its own details
            # and I'm not sure there's a way to see that we're using
            # the GitHub actions user except noting that it fails
            return GITHUB_ACTIONS_LOGIN
        raise

    else:
        return response.login


def post_comment(
    github: github_client.GitHub,
    me: str,
    repository: str,
    pr_number: int,
    contents: str,
    marker: str,
) -> None:

    issue_comments_path = github.repos(repository).issues(pr_number).comments
    comments_path = github.repos(repository).issues.comments

    for comment in issue_comments_path.get():
        if comment.user.login == me and marker in comment.body:
            log.info("Update previous comment")
            comments_path(comment.id).patch(body=contents)
            break
    else:
        log.info("Adding new comment")
        try:
            issue_comments_path.post(body=contents)
        except github_client.Forbidden as exc:
            raise CannotPostComment from exc


def set_output(**kwargs: Any) -> None:
    for key, value in kwargs.items():
        print(f"::set-output name={key}::{json.dumps(value)}")
