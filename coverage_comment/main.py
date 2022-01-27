import logging
import os

from coverage_comment import badge, comment_file
from coverage_comment import coverage as coverage_module
from coverage_comment import github, log, settings, template, wiki


def main():
    logging.basicConfig(level="INFO")

    log.info("Starting action")
    config = settings.Config.from_environ(environ=os.environ)
    return action(config=config)


def action(config: settings.Config):
    if config.VERBOSE:
        logging.getLogger().setLevel("DEBUG")
        log.debug(f"Settings: {config}")

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
            return generate_comment(config=config, coverage=coverage)
        elif event_name == "push":
            return save_badge(config=config, coverage=coverage)

    elif event_name == "workflow_run":
        return post_comment(config=config)

    log.info("Ending action")
    return 0


def generate_comment(config: settings.Config, coverage=coverage_module.Coverage):
    log.info("Generating comment for PR")

    diff_coverage = coverage_module.get_diff_coverage_info(
        base_ref=config.GITHUB_BASE_REF
    )
    previous_coverage_data_file = wiki.get_file_contents(
        repository=config.GITHUB_REPOSITORY, filename=config.BADGE_FILENAME
    )
    previous_coverage = None
    if previous_coverage_data_file:
        previous_coverage = badge.parse_badge(contents=previous_coverage_data_file)

    comment = template.get_markdown_comment(
        coverage=coverage,
        diff_coverage=diff_coverage,
        previous_coverage_rate=previous_coverage,
        template=template.read_template_file(),
    )

    try:
        gh = github.get_api(token=config.GITHUB_TOKEN)
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


def post_comment(config: settings.Config):
    log.info("Posting comment to PR")

    if not config.GITHUB_PR_RUN_ID:
        log.error("Missing input GITHUB_PR_RUN_ID. Please consult the documentation.")
        return 1

    gh = github.get_api(token=config.GITHUB_TOKEN)
    me = github.get_my_login(github=gh)
    log.info(f"Search for PR associated with run id {config.GITHUB_PR_RUN_ID}")
    try:
        pr_number = github.get_pr_number_from_workflow_run(
            github=gh,
            run_id=config.GITHUB_PR_RUN_ID,
            repository=config.GITHUB_REPOSITORY,
        )
    except github.CannotDeterminePR:
        log.info(
            "The PR cannot be found. That's strange. Please open an "
            "issue at https://github.com/ewjoachim/python-coverage-comment-action"
        )
        raise

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
            "already posted by a previous step."
        )
        log.error(exc_info=True)
        return
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


def save_badge(config: settings.Config, coverage=coverage_module.Coverage):
    is_default_branch = github.is_default_branch(
        github=github.get_api(token=config.GITHUB_TOKEN),
        repository=config.GITHUB_REPOSITORY,
        branch=config.GITHUB_REF,
    )
    log.debug(f"On default branch: {is_default_branch}")
    if not is_default_branch:
        log.info("Skipping badge save as we're not on the default branch")
        return
    log.info("Saving Badge into the repo wiki")
    badge_info = badge.compute_badge(
        line_rate=coverage.info.percent_covered,
        minimum_green=config.MINIMUM_GREEN,
        minimum_orange=config.MINIMUM_ORANGE,
    )
    wiki.upload_file(
        github_token=config.GITHUB_TOKEN,
        repository=config.GITHUB_REPOSITORY,
        filename=config.BADGE_FILENAME,
        contents=badge_info,
    )
    url = wiki.get_wiki_file_url(
        repository=config.GITHUB_REPOSITORY, filename=config.BADGE_FILENAME
    )

    badge_url = badge.get_badge_shield_url(json_url=url)
    log.info(f"Badge JSON stored at {url}")
    log.info(f"Badge URL: {badge_url}")
