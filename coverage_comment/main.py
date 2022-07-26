import functools
import logging
import os
import sys

import httpx

from coverage_comment import comment_file, communication
from coverage_comment import coverage as coverage_module
from coverage_comment import (
    files,
    github,
    github_client,
    log,
    settings,
    storage,
    subprocess,
    template,
)


def main():
    logging.basicConfig(level="INFO")

    log.info("Starting action")
    config = settings.Config.from_environ(environ=os.environ)
    if config.VERBOSE:
        logging.getLogger().setLevel("DEBUG")
        log.debug(f"Settings: {config}")

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
        coverage = coverage_module.get_coverage_info(merge=config.MERGE_COVERAGE_FILES)
        if event_name == "pull_request":
            return generate_comment(
                config=config,
                coverage=coverage,
                github_session=github_session,
            )
        else:
            # event_name == "push"
            return save_badge(
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
    github_session: httpx.Client,
) -> int:
    log.info("Generating comment for PR")

    gh = github_client.GitHub(session=github_session)

    diff_coverage = coverage_module.get_diff_coverage_info(
        base_ref=config.GITHUB_BASE_REF
    )
    previous_coverage_data_file = storage.get_datafile_contents(
        github=gh,
        repository=config.GITHUB_REPOSITORY,
        branch=config.COVERAGE_DATA_BRANCH,
    )
    previous_coverage = None
    if previous_coverage_data_file:
        previous_coverage = files.parse_datafile(contents=previous_coverage_data_file)

    try:
        comment = template.get_markdown_comment(
            coverage=coverage,
            diff_coverage=diff_coverage,
            previous_coverage_rate=previous_coverage,
            base_template=template.read_template_file(),
            custom_template=config.COMMENT_TEMPLATE,
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
    try:
        if config.FORCE_WORKFLOW_RUN:
            raise github.CannotPostComment

        github.post_comment(
            github=gh,
            me=github.get_my_login(github=gh),
            repository=config.GITHUB_REPOSITORY,
            pr_number=config.GITHUB_PR_NUMBER,
            contents=comment,
            marker=template.MARKER,
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
            filename=config.COMMENT_FILENAME,
            content=comment,
        )
        github.set_output(COMMENT_FILE_WRITTEN=True)
        log.debug("Comment stored locally on disk")
    else:
        github.set_output(COMMENT_FILE_WRITTEN=False)
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
            "issue at https://github.com/ewjoachim/python-coverage-comment-action",
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
            filename=config.COMMENT_FILENAME,
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
        marker=template.MARKER,
    )
    log.info("Comment posted in PR")

    return 0


def save_badge(
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

    log.info("Saving coverage files & badge into the repository")
    files_to_save = files.compute_files(
        line_rate=coverage.info.percent_covered,
        minimum_green=config.MINIMUM_GREEN,
        minimum_orange=config.MINIMUM_ORANGE,
        http_session=http_session,
    )
    is_public = repo_info.is_public()
    url_getter = functools.partial(
        storage.get_file_url,
        is_public=is_public,
        repository=config.GITHUB_REPOSITORY,
        branch=config.COVERAGE_DATA_BRANCH,
    )
    readme_file, log_message = communication.get_readme_and_log(
        readme_url=storage.get_readme_url(
            branch=config.COVERAGE_DATA_BRANCH,
            repository=config.GITHUB_REPOSITORY,
        ),
        image_urls=files.get_urls(url_getter=url_getter),
        is_public=is_public,
    )
    storage.upload_files(
        files=files_to_save,
        git=git,
        branch=config.COVERAGE_DATA_BRANCH,
        initial_file=readme_file,
    )

    log.info(log_message)

    return 0
