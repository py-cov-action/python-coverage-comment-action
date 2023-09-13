import os

import httpx

from coverage_comment import main, settings, subprocess


def test_main(mocker, get_logs):
    # This test is a mock festival. The idea is that all the things that are hard
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
            "GITHUB_STEP_SUMMARY": "step_summary",
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


def test_main__exception(mocker, get_logs):
    # This test simulates an exception in the main part of the action. This should be catched and logged.
    exit = mocker.patch("sys.exit")
    mocker.patch(
        "coverage_comment.main.action", side_effect=Exception("Mocked exception")
    )

    os.environ.update(
        {
            "GITHUB_REPOSITORY": "foo/bar",
            "GITHUB_PR_RUN_ID": "",
            "GITHUB_REF": "ref",
            "GITHUB_TOKEN": "token",
            "GITHUB_BASE_REF": "",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_STEP_SUMMARY": "step_summary",
        }
    )
    main.main()
    exit.assert_called_with(1)

    assert get_logs("ERROR", "Critical error")
