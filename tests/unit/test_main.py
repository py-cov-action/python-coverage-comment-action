import logging
import os

import httpx

from coverage_comment import main, settings, subprocess


def test_action__invalid_event_name(push_config, get_logs):
    result = main.action(
        config=push_config(GITHUB_EVENT_NAME="pull_request_target"),
        github_session=None,
        http_session=None,
        git=None,
    )

    assert result == 1
    assert get_logs("ERROR", "This action has only been designed to work for")


def test_post_comment__no_run_id(workflow_run_config, get_logs):
    result = main.post_comment(
        config=workflow_run_config(GITHUB_PR_RUN_ID=""),
        github_session=None,
    )

    assert result == 1
    assert get_logs("ERROR", "Missing input GITHUB_PR_RUN_ID")


def test_main(mocker, get_logs):
    # This test is a mock frienzy. The idea is that all the things that are hard
    # to simulate without mocks have been pushed up the stack up to this function
    # so this is THE place where we have no choice but to mock.
    # We could also accept not to test this function but if we've come this
    # far and have 98% coverage, we can as well have 100%.

    exit = mocker.patch("sys.exit")
    action = mocker.patch("coverage_comment.main.action")

    os.environ.update(
        {
            "GITHUB_REPOSITORY": "foo/bar",
            "GITHUB_PR_RUN_ID": "",
            "GITHUB_REF": "ref",
            "GITHUB_TOKEN": "token",
            "GITHUB_BASE_REF": "",
            "GITHUB_EVENT_NAME": "push",
        }
    )
    main.main()

    exit.assert_called_with(action.return_value)
    kwargs = action.call_args_list[0].kwargs
    assert isinstance(kwargs["config"], settings.Config)
    assert isinstance(kwargs["git"], subprocess.Git)
    assert isinstance(kwargs["github_session"], httpx.Client)
    assert isinstance(kwargs["http_session"], httpx.Client)

    assert get_logs("INFO", "Starting action")
    assert get_logs("INFO", "Ending action")


def test_main__verbose(mocker, get_logs, caplog):
    # This test is a mock frienzy. The idea is that all the things that are hard
    # to simulate without mocks have been pushed up the stack up to this function
    # so this is THE place where we have no choice but to mock.
    # We could also accept not to test this function but if we've come this
    # far and have 98% coverage, we can as well have 100%.

    mocker.patch("sys.exit")
    mocker.patch("coverage_comment.main.action")

    os.environ.update(
        {
            "GITHUB_REPOSITORY": "foo/bar",
            "GITHUB_PR_RUN_ID": "",
            "GITHUB_REF": "ref",
            "GITHUB_TOKEN": "token",
            "GITHUB_BASE_REF": "",
            "GITHUB_EVENT_NAME": "push",
            "VERBOSE": "true",
        }
    )
    main.main()

    assert get_logs("DEBUG", "Settings: Config(")
    assert logging.getLevelName(logging.getLogger().level) == "DEBUG"
