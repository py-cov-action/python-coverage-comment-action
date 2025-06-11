from __future__ import annotations

import functools
import json
import logging
import os
import sys

import httpx

from coverage_comment import activity as activity_module
from coverage_comment import (
    comment_file,
    communication,
    diff_grouper,
    files,
    github,
    github_client,
    log,
    log_utils,
    settings,
    storage,
    subprocess,
    template,
)
from coverage_comment import coverage as coverage_module


def main():
    try:
        logging.basicConfig(level="DEBUG")
        logging.getLogger().handlers[0].formatter = log_utils.GitHubFormatter()

        log.info("Starting action")
        config = settings.Config.from_environ(environ=os.environ)

        git = subprocess.Git()

        with (
            httpx.Client(
                base_url=config.GITHUB_BASE_URL,
                follow_redirects=True,
                headers={"Authorization": f"token {config.GITHUB_TOKEN}"},
            ) as github_session,
            httpx.Client() as http_session,
        ):
            exit_code = action(
                config=config,
                github_session=github_session,
                http_session=http_session,
                git=git,
            )

        log.info("Ending action")
        sys.exit(exit_code)

    except Exception:
        log.exception(
            "Critical error. This error possibly occurred because the permissions of the workflow are set incorrectly. You can see the correct setting of permissions here: https://github.com/py-cov-action/python-coverage-comment-action#basic-usage\nOtherwise please look for open issues or open one in https://github.com/py-cov-action/python-coverage-comment-action/"
        )
        sys.exit(1)


def action(
    config: settings.Config,
    github_session: httpx.Client,
    http_session: httpx.Client,
    git: subprocess.Git,
) -> int:
    log.debug(f"Operating on {config.GITHUB_REF}")
    gh = github_client.GitHub(session=github_session)
    event_name = config.GITHUB_EVENT_NAME
    event_path = config.GITHUB_EVENT_PATH
    event_action = None

    if event_path and os.path.exists(event_path):
        with open(event_path) as event_file:
            event_payload = json.load(event_file)
        is_merged_pr_action = event_payload.get("pull_request", {}).get("merged", False)
        if is_merged_pr_action:
            event_action = "merged"

    repo_info = github.get_repository_info(
        github=gh, repository=config.GITHUB_REPOSITORY
    )
    try:
        activity = activity_module.find_activity(
            event_name=event_name,
            event_action=event_action,
            is_default_branch=repo_info.is_default_branch(ref=config.GITHUB_REF),
        )
    except activity_module.ActivityNotFound:
        log.error(
            'This action has only been designed to work for "pull_request", "push", '
            f'"workflow_run" or "schedule" actions, not "{event_name}". Because there '
            "are security implications. If you have a different usecase, please open an issue, "
            "we'll be glad to add compatibility."
        )
        return 1

    if activity == "save_coverage_data_files":
        return save_coverage_data_files(
            config=config,
            git=git,
            http_session=http_session,
            repo_info=repo_info,
        )

    elif activity == "process_pr":
        return process_pr(
            config=config,
            gh=gh,
            repo_info=repo_info,
            git=git,
        )

    else:
        # activity == "post_comment":
        return post_comment(
            config=config,
            gh=gh,
        )


def process_pr(
    config: settings.Config,
    gh: github_client.GitHub,
    repo_info: github.RepositoryInfo,
    git: subprocess.Git,
) -> int:
    log.info("Generating comment for PR")

    if not config.GITHUB_PR_NUMBER and not config.GITHUB_BRANCH_NAME:
        log.info(
            "This worflow is not triggered on a pull_request event, "
            "nor on a push event on a branch. Consequently, there's nothing to do. "
            "Exiting."
        )
        return 0

    _, coverage = coverage_module.get_coverage_info(
        merge=config.MERGE_COVERAGE_FILES,
        coverage_path=config.COVERAGE_PATH,
    )
    base_ref = config.GITHUB_BASE_REF or repo_info.default_branch

    added_lines = coverage_module.get_added_lines(git=git, base_ref=base_ref)
    diff_coverage = coverage_module.get_diff_coverage_info(
        coverage=coverage, added_lines=added_lines
    )
    # It only really makes sense to display a comparison with the previous
    # coverage if the PR target is the branch in which the coverage data is
    # stored, e.g. the default branch.
    # In the case we're running on a branch without a PR yet, we can't know
    # if it's going to target the default branch, so we display it.
    previous_coverage_data_file = None
    pr_targets_default_branch = base_ref == repo_info.default_branch

    if pr_targets_default_branch:
        previous_coverage_data_file = storage.get_datafile_contents(
            github=gh,
            repository=config.GITHUB_REPOSITORY,
            branch=config.FINAL_COVERAGE_DATA_BRANCH,
        )

    previous_coverage, previous_coverage_rate = None, None
    if previous_coverage_data_file:
        previous_coverage, previous_coverage_rate = files.parse_datafile(
            contents=previous_coverage_data_file
        )

    marker = template.get_marker(marker_id=config.SUBPROJECT_ID)

    files_info, count_files = template.select_files(
        coverage=coverage,
        diff_coverage=diff_coverage,
        previous_coverage=previous_coverage,
        max_files=config.MAX_FILES_IN_COMMENT,
    )
    try:
        comment = template.get_comment_markdown(
            coverage=coverage,
            diff_coverage=diff_coverage,
            previous_coverage=previous_coverage,
            previous_coverage_rate=previous_coverage_rate,
            files=files_info,
            count_files=count_files,
            max_files=config.MAX_FILES_IN_COMMENT,
            minimum_green=config.MINIMUM_GREEN,
            minimum_orange=config.MINIMUM_ORANGE,
            github_host=github.extract_github_host(config.GITHUB_BASE_URL),
            repo_name=config.GITHUB_REPOSITORY,
            pr_number=config.GITHUB_PR_NUMBER,
            base_template=template.read_template_file("comment.md.j2"),
            custom_template=config.COMMENT_TEMPLATE,
            pr_targets_default_branch=pr_targets_default_branch,
            marker=marker,
            subproject_id=config.SUBPROJECT_ID,
        )
        # Same as above except `max_files` is None
        summary_comment = template.get_comment_markdown(
            coverage=coverage,
            diff_coverage=diff_coverage,
            previous_coverage=previous_coverage,
            previous_coverage_rate=previous_coverage_rate,
            files=files_info,
            count_files=count_files,
            max_files=None,
            minimum_green=config.MINIMUM_GREEN,
            minimum_orange=config.MINIMUM_ORANGE,
            github_host=github.extract_github_host(config.GITHUB_BASE_URL),
            repo_name=config.GITHUB_REPOSITORY,
            pr_number=config.GITHUB_PR_NUMBER,
            base_template=template.read_template_file("comment.md.j2"),
            custom_template=config.COMMENT_TEMPLATE,
            pr_targets_default_branch=pr_targets_default_branch,
            marker=marker,
            subproject_id=config.SUBPROJECT_ID,
        )
    except template.MissingMarker:
        log.error(
            "Marker not found. This error can happen if you defined a custom comment "
            "template that doesn't inherit the base template and you didn't include "
            "``{{ marker }}``. The marker is necessary for this action to recognize "
            "its own comment and avoid making new comments or overwriting someone else's "
            "comment."
        )
        return 1
    except template.TemplateError:
        log.exception(
            "There was a rendering error when computing the text of the comment to post "
            "on the PR. Please see the traceback, in particular if you're using a custom "
            "template."
        )
        return 1

    github.add_job_summary(
        content=summary_comment, github_step_summary=config.GITHUB_STEP_SUMMARY
    )
    pr_number: int | None = config.GITHUB_PR_NUMBER
    if pr_number is None:
        # If we don't have a PR number, we're launched from a push event,
        # so we need to find the PR number from the branch name
        try:
            pr_number = github.find_pr_for_branch(
                github=gh,
                # A push event cannot be initiated from a forked repository
                repository=config.GITHUB_REPOSITORY,
                owner=config.GITHUB_REPOSITORY.split("/")[0],
                branch=config.GITHUB_BRANCH_NAME,
            )
        except github.CannotDeterminePR:
            pr_number = None

    if pr_number is not None and config.ANNOTATE_MISSING_LINES:
        annotations = diff_grouper.get_diff_missing_groups(
            coverage=coverage, diff_coverage=diff_coverage
        )
        github.create_missing_coverage_annotations(
            annotation_type=config.ANNOTATION_TYPE,
            annotations=[
                (annotation.file, annotation.line_start, annotation.line_end)
                for annotation in annotations
            ],
        )

    try:
        if config.FORCE_WORKFLOW_RUN or not pr_number:
            raise github.CannotPostComment

        github.post_comment(
            github=gh,
            me=github.get_my_login(github=gh),
            repository=config.GITHUB_REPOSITORY,
            pr_number=pr_number,
            contents=comment,
            marker=marker,
        )
    except github.CannotPostComment:
        log.debug("Exception when posting comment", exc_info=True)
        log.info(
            "Cannot post comment. This is probably because this is an external PR, so "
            "it's expected. Ensure you have an additional `workflow_run` step "
            "configured as explained in the documentation (or alternatively, give up "
            "on PR comments for external PRs)."
        )
        comment_file.store_file(
            filename=config.FINAL_COMMENT_FILENAME,
            content=comment,
        )
        github.set_output(github_output=config.GITHUB_OUTPUT, COMMENT_FILE_WRITTEN=True)
        log.debug("Comment stored locally on disk")
    else:
        github.set_output(
            github_output=config.GITHUB_OUTPUT, COMMENT_FILE_WRITTEN=False
        )
        log.debug("Comment not generated")

    return 0


def post_comment(
    config: settings.Config,
    gh: github_client.GitHub,
) -> int:
    log.info("Posting comment to PR")

    if not config.GITHUB_PR_RUN_ID:
        log.error("Missing input GITHUB_PR_RUN_ID. Please consult the documentation.")
        return 1

    me = github.get_my_login(github=gh)
    log.info(f"Search for PR associated with run id {config.GITHUB_PR_RUN_ID}")
    owner, branch = github.get_branch_from_workflow_run(
        github=gh,
        run_id=config.GITHUB_PR_RUN_ID,
        repository=config.GITHUB_REPOSITORY,
    )
    try:
        pr_number = github.find_pr_for_branch(
            github=gh,
            repository=config.GITHUB_REPOSITORY,
            owner=owner,
            branch=branch,
        )
    except github.CannotDeterminePR:
        log.error(
            "The PR cannot be found. That's strange. Please open an "
            "issue at https://github.com/py-cov-action/python-coverage-comment-action",
            exc_info=True,
        )
        return 1

    log.info(f"PR number: {pr_number}")
    log.info("Download associated artifacts")
    try:
        comment = github.download_artifact(
            github=gh,
            repository=config.GITHUB_REPOSITORY,
            artifact_name=config.COMMENT_ARTIFACT_NAME,
            run_id=config.GITHUB_PR_RUN_ID,
            filename=config.FINAL_COMMENT_FILENAME,
        )
    except github.NoArtifact:
        log.info(
            "Artifact was not found, which is probably because it was probably "
            "already posted by a previous step.",
            exc_info=True,
        )
        return 0
    log.info("Comment file found in artifact, posting to PR")
    github.post_comment(
        github=gh,
        me=me,
        repository=config.GITHUB_REPOSITORY,
        pr_number=pr_number,
        contents=comment,
        marker=template.get_marker(marker_id=config.SUBPROJECT_ID),
    )
    log.info("Comment posted in PR")

    return 0


def save_coverage_data_files(
    config: settings.Config,
    git: subprocess.Git,
    http_session: httpx.Client,
    repo_info: github.RepositoryInfo,
) -> int:
    log.info("Computing coverage files & badge")

    raw_coverage_data, coverage = coverage_module.get_coverage_info(
        merge=config.MERGE_COVERAGE_FILES,
        coverage_path=config.COVERAGE_PATH,
    )

    operations: list[files.Operation] = files.compute_files(
        line_rate=coverage.info.percent_covered,
        raw_coverage_data=raw_coverage_data,
        coverage_path=config.COVERAGE_PATH,
        minimum_green=config.MINIMUM_GREEN,
        minimum_orange=config.MINIMUM_ORANGE,
        http_session=http_session,
    )

    is_public = repo_info.is_public()
    if is_public:
        log.info("Generating HTML coverage report")
        operations.append(
            files.get_coverage_html_files(coverage_path=config.COVERAGE_PATH)
        )

    markdown_report = coverage_module.generate_coverage_markdown(
        coverage_path=config.COVERAGE_PATH
    )

    github.add_job_summary(
        content=f"## Coverage report\n\n{markdown_report}",
        github_step_summary=config.GITHUB_STEP_SUMMARY,
    )

    github_host = github.extract_github_host(config.GITHUB_BASE_URL)
    url_getter = functools.partial(
        storage.get_raw_file_url,
        github_host=github_host,
        is_public=is_public,
        repository=config.GITHUB_REPOSITORY,
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
    )
    readme_url = storage.get_repo_file_url(
        github_host=github_host,
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
        repository=config.GITHUB_REPOSITORY,
    )
    html_report_url = storage.get_html_report_url(
        github_host=github_host,
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
        repository=config.GITHUB_REPOSITORY,
        use_gh_pages_html_url=config.USE_GH_PAGES_HTML_URL,
    )
    readme_file, log_message = communication.get_readme_and_log(
        is_public=is_public,
        readme_url=readme_url,
        image_urls=files.get_urls(url_getter=url_getter),
        html_report_url=html_report_url,
        markdown_report=markdown_report,
        subproject_id=config.SUBPROJECT_ID,
    )
    operations.append(readme_file)
    storage.commit_operations(
        operations=operations,
        git=git,
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
    )

    log.info(log_message)

    return 0
