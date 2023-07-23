import functools
import logging
import os
import sys

import httpx

from coverage_comment import annotations, comment_file, communication
from coverage_comment import coverage as coverage_module
from coverage_comment import (
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


def main():
    try:
        logging.basicConfig(level="DEBUG")
        logging.getLogger().handlers[0].formatter = log_utils.GitHubFormatter()

        log.info("Starting action")
        config = settings.Config.from_environ(environ=os.environ)

        github_session = httpx.Client(
            base_url="https://api.github.com",
            follow_redirects=True,
            headers={"Authorization": f"token {config.GITHUB_TOKEN}"},
        )
        http_session = httpx.Client()
        git = subprocess.Git()

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

    event_name = config.GITHUB_EVENT_NAME
    if event_name not in {"pull_request", "push", "workflow_run"}:
        log.error(
            'This action has only been designed to work for "pull_request", "branch" '
            f'or "workflow_run" actions, not "{event_name}". Because there are security '
            "implications. If you have a different usecase, please open an issue, "
            "we'll be glad to add compatibility."
        )
        return 1

    if event_name in {"pull_request", "push"}:
        coverage = coverage_module.get_coverage_info(
            merge=config.MERGE_COVERAGE_FILES, coverage_path=config.COVERAGE_PATH
        )
        if event_name == "pull_request":
            diff_coverage = coverage_module.get_diff_coverage_info(
                base_ref=config.GITHUB_BASE_REF, coverage_path=config.COVERAGE_PATH
            )
            if config.ANNOTATE_MISSING_LINES:
                annotations.create_pr_annotations(
                    annotation_type=config.ANNOTATION_TYPE, diff_coverage=diff_coverage
                )
            return generate_comment(
                config=config,
                coverage=coverage,
                diff_coverage=diff_coverage,
                github_session=github_session,
            )
        else:
            # event_name == "push"
            return save_coverage_data_files(
                config=config,
                coverage=coverage,
                github_session=github_session,
                git=git,
                http_session=http_session,
            )

    else:
        # event_name == "workflow_run"
        return post_comment(
            config=config,
            github_session=github_session,
        )


def generate_comment(
    config: settings.Config,
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
    github_session: httpx.Client,
) -> int:
    log.info("Generating comment for PR")

    gh = github_client.GitHub(session=github_session)

    previous_coverage_data_file = storage.get_datafile_contents(
        github=gh,
        repository=config.GITHUB_REPOSITORY,
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
    )
    previous_coverage = None
    if previous_coverage_data_file:
        previous_coverage = files.parse_datafile(contents=previous_coverage_data_file)

    marker = template.get_marker(marker_id=config.SUBPROJECT_ID)
    try:
        comment = template.get_comment_markdown(
            coverage=coverage,
            diff_coverage=diff_coverage,
            previous_coverage_rate=previous_coverage,
            base_template=template.read_template_file("comment.md.j2"),
            custom_template=config.COMMENT_TEMPLATE,
            marker=marker,
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

    assert config.GITHUB_PR_NUMBER

    github.add_job_summary(
        content=comment, github_step_summary=config.GITHUB_STEP_SUMMARY
    )

    try:
        if config.FORCE_WORKFLOW_RUN:
            raise github.CannotPostComment

        github.post_comment(
            github=gh,
            me=github.get_my_login(github=gh),
            repository=config.GITHUB_REPOSITORY,
            pr_number=config.GITHUB_PR_NUMBER,
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


def post_comment(config: settings.Config, github_session: httpx.Client) -> int:
    log.info("Posting comment to PR")

    if not config.GITHUB_PR_RUN_ID:
        log.error("Missing input GITHUB_PR_RUN_ID. Please consult the documentation.")
        return 1

    gh = github_client.GitHub(session=github_session)
    me = github.get_my_login(github=gh)
    log.info(f"Search for PR associated with run id {config.GITHUB_PR_RUN_ID}")
    try:
        pr_number = github.get_pr_number_from_workflow_run(
            github=gh,
            run_id=config.GITHUB_PR_RUN_ID,
            repository=config.GITHUB_REPOSITORY,
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
    coverage: coverage_module.Coverage,
    github_session: httpx.Client,
    git: subprocess.Git,
    http_session: httpx.Client,
) -> int:
    gh = github_client.GitHub(session=github_session)
    repo_info = github.get_repository_info(
        github=gh,
        repository=config.GITHUB_REPOSITORY,
    )
    is_default_branch = repo_info.is_default_branch(ref=config.GITHUB_REF)
    log.debug(f"On default branch: {is_default_branch}")

    if not is_default_branch:
        log.info("Skipping badge save as we're not on the default branch")
        return 0

    log.info("Computing coverage files & badge")
    operations: list[files.Operation] = files.compute_files(
        line_rate=coverage.info.percent_covered,
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

    url_getter = functools.partial(
        storage.get_raw_file_url,
        is_public=is_public,
        repository=config.GITHUB_REPOSITORY,
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
    )
    readme_url = storage.get_repo_file_url(
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
        repository=config.GITHUB_REPOSITORY,
    )
    html_report_url = storage.get_html_report_url(
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
        repository=config.GITHUB_REPOSITORY,
    )
    readme_file, log_message = communication.get_readme_and_log(
        is_public=is_public,
        readme_url=readme_url,
        image_urls=files.get_urls(url_getter=url_getter),
        html_report_url=html_report_url,
        markdown_report=markdown_report,
    )
    operations.append(readme_file)
    storage.commit_operations(
        operations=operations,
        git=git,
        branch=config.FINAL_COVERAGE_DATA_BRANCH,
    )

    log.info(log_message)

    return 0
