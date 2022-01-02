import logging
import os
import sys

from coverage_comment import badge, comment_file
from coverage_comment import coverage as coverage_module
from coverage_comment import github, log, settings, template, wiki


def main():
    logging.basicConfig(level="INFO")

    log.info("Starting action")
    config = settings.Config.from_environ(environ=os.environ)

    if config.VERBOSE:
        logging.getLogger().setLevel("DEBUG")

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
    if previous_coverage_data_file:
        previous_coverage = badge.parse_badge(contents=previous_coverage_data_file)

    comment = template.get_markdown_comment(
        coverage=coverage,
        diff_coverage=diff_coverage,
        previous_coverage_rate=previous_coverage,
        template=template.read_template_file(),
    )
    log.debug(f"Comment: \n{comment}")

    comment_file.store_file(filename=config.COMMENT_FILENAME, content=comment)
    log.debug("Comment stored locally on disk")


def post_comment(config: settings.Config):
    log.info("Posting comment to PR")

    if not config.GITHUB_PR_RUN_ID:
        log.error("Missing input GITHUB_PR_RUN_ID. Please consult the documentation.")
        return 1

    gh = github.get_api(token=config.GITHUB_TOKEN)
    me = github.get_my_login(github=gh)
    pr_number = github.get_pr_number_from_workflow_run(
        github=gh,
        run_id=config.GITHUB_PR_RUN_ID,
        repository=config.GITHUB_REPOSITORY,
    )
    log.info(f"PR number: {pr_number}")
    comment = github.download_artifact(
        github=gh,
        repository=config.GITHUB_REPOSITORY,
        artifact_name=config.COMMENT_ARTIFACT_NAME,
        run_id=config.GITHUB_PR_RUN_ID,
        filename=config.COMMENT_FILENAME,
    )

    github.post_comment(
        github=gh,
        me=me,
        repository=config.GITHUB_REPOSITORY,
        pr_number=pr_number,
        contents=comment,
        marker=template.MARKER,
    )


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


if __name__ == "__main__":
    sys.exit(main())
