from __future__ import annotations

import dataclasses
import io
import json
import pathlib
import sys
import zipfile
from urllib.parse import urlparse

from coverage_comment import github_client, log

GITHUB_ACTIONS_LOGIN = "github-actions[bot]"


class CannotDeterminePR(Exception):
    pass


class CannotPostComment(Exception):
    pass


class NoArtifact(Exception):
    pass


@dataclasses.dataclass
class RepositoryInfo:
    default_branch: str
    visibility: str

    def is_default_branch(self, ref: str) -> bool:
        return f"refs/heads/{self.default_branch}" == ref

    def is_public(self) -> bool:
        return self.visibility == "public"


def get_repository_info(
    github: github_client.GitHub, repository: str
) -> RepositoryInfo:
    response = github.repos(repository).get()

    return RepositoryInfo(
        default_branch=response.default_branch, visibility=response.visibility
    )


def extract_github_host(api_url: str) -> str:
    """
    Extracts the base GitHub web host URL from a GitHub API URL.

    Args:
      api_url: The GitHub API URL (e.g., 'https://api.github.com/...',
               'https://my-ghe.company.com/api/v3/...').

    Returns:
      The base GitHub web host URL (e.g., 'https://github.com',
      'https://my-ghe.company.com').
    """
    parsed_url = urlparse(api_url)
    scheme = parsed_url.scheme
    netloc = parsed_url.netloc  # This includes the domain and potentially the port

    # Special case for GitHub.com API
    if netloc == "api.github.com":
        host_domain = "github.com"
    # Special case for GitHub.com with port (less common but good practice)
    elif netloc.startswith("api.github.com:"):
        # Remove 'api.' prefix but keep the port
        host_domain = netloc.replace("api.", "", 1)
    # General case for GitHub Enterprise (netloc is already the host:port)
    else:
        host_domain = netloc

    # Reconstruct the host URL
    host_url = f"{scheme}://{host_domain}"

    return host_url


def download_artifact(
    github: github_client.GitHub,
    repository: str,
    artifact_name: str,
    run_id: int,
    filename: pathlib.Path,
) -> str:
    repo_path = github.repos(repository)

    try:
        artifact = next(
            artifact
            for artifact in _fetch_artifacts(repo_path, run_id)
            if artifact.name == artifact_name
        )
    except StopIteration:
        raise NoArtifact(f"No artifact found with name {artifact_name} in run {run_id}")

    zip_bytes = io.BytesIO(repo_path.actions.artifacts(artifact.id).zip.get(bytes=True))
    zipf = zipfile.ZipFile(zip_bytes)

    try:
        return zipf.open(str(filename), "r").read().decode("utf-8")
    except KeyError:
        raise NoArtifact(f"File named {filename} not found in artifact {artifact_name}")


def _fetch_artifacts(repo_path, run_id):
    page = 1
    total_fetched = 0

    while True:
        result = repo_path.actions.runs(run_id).artifacts.get(page=str(page))
        if not result or not result.artifacts:
            break

        yield from result.artifacts

        total_fetched += len(result.artifacts)
        if total_fetched >= result.total_count:
            break

        page += 1


def get_branch_from_workflow_run(
    github: github_client.GitHub, repository: str, run_id: int
) -> tuple[str, str]:
    repo_path = github.repos(repository)
    run = repo_path.actions.runs(run_id).get()
    branch = run.head_branch
    owner = run.head_repository.owner.login
    return owner, branch


def find_pr_for_branch(
    github: github_client.GitHub, repository: str, owner: str, branch: str
) -> int:
    # The full branch is in the form of "owner:branch" as specified in
    # https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests
    # but it seems to also work with "owner/repo:branch"

    full_branch = f"{owner}:{branch}"

    common_kwargs = {"head": full_branch, "sort": "updated", "direction": "desc"}
    try:
        return next(
            iter(
                pr.number
                for pr in github.repos(repository).pulls.get(
                    state="open", **common_kwargs
                )
            )
        )
    except StopIteration:
        pass
    log.info(f"No open PR found for branch {branch}, defaulting to all PRs")

    try:
        return next(
            iter(
                pr.number
                for pr in github.repos(repository).pulls.get(
                    state="all", **common_kwargs
                )
            )
        )
    except StopIteration:
        raise CannotDeterminePR(f"No open PR found for branch {branch}")


def get_my_login(github: github_client.GitHub) -> str:
    try:
        response = github.user.get()
    except github_client.Forbidden:
        # The GitHub actions user cannot access its own details
        # and I'm not sure there's a way to see that we're using
        # the GitHub actions user except noting that it fails
        return GITHUB_ACTIONS_LOGIN

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
            try:
                comments_path(comment.id).patch(body=contents)
            except github_client.Forbidden as exc:
                raise CannotPostComment from exc
            break
    else:
        log.info("Adding new comment")
        try:
            issue_comments_path.post(body=contents)
        except github_client.Forbidden as exc:
            raise CannotPostComment from exc


def set_output(github_output: pathlib.Path | None, **kwargs: bool) -> None:
    if github_output:
        with github_output.open("a") as f:
            for key, value in kwargs.items():
                f.write(f"{key}={json.dumps(value)}\n")


def escape_property(s: str) -> str:
    return (
        s.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def escape_data(s: str) -> str:
    return s.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def get_workflow_command(command: str, command_value: str, **kwargs: str) -> str:
    """
    Returns a string that can be printed to send a workflow command
    https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions
    """
    values_listed = [f"{key}={escape_property(value)}" for key, value in kwargs.items()]

    context = f" {','.join(values_listed)}" if values_listed else ""
    return f"::{command}{context}::{escape_data(command_value)}"


def send_workflow_command(command: str, command_value: str, **kwargs: str) -> None:
    print(
        get_workflow_command(command=command, command_value=command_value, **kwargs),
        file=sys.stderr,
    )


def create_missing_coverage_annotations(
    annotation_type: str, annotations: list[tuple[pathlib.Path, int, int]]
):
    """
    Create annotations for lines with missing coverage.

    annotation_type: The type of annotation to create. Can be either "error" or "warning".
    annotations: A list of tuples of the form (file, line_start, line_end)
    """
    send_workflow_command(
        command="group", command_value="Annotations of lines with missing coverage"
    )
    for file, line_start, line_end in annotations:
        if line_start == line_end:
            message = f"Missing coverage on line {line_start}"
        else:
            message = f"Missing coverage on lines {line_start}-{line_end}"

        send_workflow_command(
            command=annotation_type,
            command_value=message,
            # This will produce \ paths when running on windows.
            # GHA doc is unclear whether this is right or not.
            file=str(file),
            line=str(line_start),
            endLine=str(line_end),
            title="Missing coverage",
        )
    send_workflow_command(command="endgroup", command_value="")


def append_to_file(content: str, filepath: pathlib.Path):
    with filepath.open(mode="a") as file:
        file.write(content)


def add_job_summary(content: str, github_step_summary: pathlib.Path):
    append_to_file(content=content, filepath=github_step_summary)
