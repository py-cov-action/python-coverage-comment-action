import pytest

from coverage_comment import subprocess, wiki


def test_git(mocker):
    run = mocker.patch("coverage_comment.subprocess.run")
    git = wiki.Git("/tmp")

    git.clone("https://some_address.git", "--depth", "1", text=True)
    git.add("some_file")

    assert run.call_args_list == [
        mocker.call(
            "git",
            "clone",
            "https://some_address.git",
            "--depth",
            "1",
            cwd="/tmp",
            text=True,
        ),
        mocker.call("git", "add", "some_file", cwd="/tmp"),
    ]


def test_git_error(mocker):
    mocker.patch(
        "coverage_comment.subprocess.run", side_effect=subprocess.SubProcessError
    )
    git = wiki.Git("/tmp")

    with pytest.raises(wiki.GitError):
        git.add("some_file")


def test_upload_file_ok(mocker):
    git = mocker.MagicMock()

    wiki.upload_file(
        github_token="foo",
        repository="bar",
        filename="baz",
        contents="qux",
        git=git,
    )

    assert git.mock_calls == [
        mocker.call.clone("https://x-access-token:foo@github.com/bar.wiki.git"),
        mocker.call.add("baz"),
        mocker.call.diff("--staged", "--exit-code"),
        mocker.call.config("--global", "user.email", "python-coverage-comment-action"),
        mocker.call.config("--global", "user.name", "python-coverage-comment-action"),
        mocker.call.commit("-m", "Update badge"),
        mocker.call.push("-u", "origin"),
    ]


def test_upload_file_no_change(mocker, caplog):
    caplog.set_level("DEBUG")
    git = mocker.MagicMock()
    git.diff.side_effect = wiki.GitError

    wiki.upload_file(
        github_token="foo",
        repository="bar",
        filename="baz",
        contents="qux",
        git=git,
    )

    assert git.mock_calls == [
        mocker.call.clone("https://x-access-token:foo@github.com/bar.wiki.git"),
        mocker.call.add("baz"),
        mocker.call.diff("--staged", "--exit-code"),
    ]
    assert "No change detected" in caplog.records[-1].message


@pytest.mark.parametrize(
    "error_message, log_expected",
    [
        ("remote error: access denied or repository not exported", True),
        ("", False),
    ],
)
def test_upload_file_push_error(mocker, caplog, error_message, log_expected):
    caplog.set_level("DEBUG")
    git = mocker.MagicMock()
    git.push.side_effect = wiki.GitError(error_message)

    with pytest.raises(wiki.GitError):
        wiki.upload_file(
            github_token="foo",
            repository="bar",
            filename="baz",
            contents="qux",
            git=git,
        )
    wiki_log_present = any(
        "Wiki seems not to be activated" in rec.message for rec in caplog.records
    )
    assert wiki_log_present is log_expected, caplog.records[-1].message


def test_get_file_contents(mocker):
    get = mocker.patch("httpx.get")
    get.return_value.text = "foo"

    assert wiki.get_file_contents(repository="foo", filename="bar") == "foo"

    get.assert_called_with("https://raw.githubusercontent.com/wiki/foo/bar")


def test_get_file_contents_not_found(mocker, caplog):
    caplog.set_level("WARNING")
    get = mocker.patch("httpx.get")
    get.side_effect = ValueError

    assert wiki.get_file_contents(repository="foo", filename="bar") is None

    assert "Previous coverage results not found" in caplog.records[-1].message
