import pathlib
from unittest.mock import patch

import pytest

from coverage_comment import subprocess, wiki


class MockGit(subprocess.Git):
    def clone(self, *args, **kwargs):
        filename = "bar"
        content = "baz"
        with open((self.cwd / filename), "wt") as f:
            f.write(content)


def test_upload_file__ok(mocker):
    git = mocker.MagicMock()
    git.diff.side_effect = subprocess.GitError

    wiki.upload_file(
        github_token="foo",
        repository="bar",
        filename=pathlib.Path("baz"),
        contents="qux",
        git=git,
    )

    assert git.mock_calls == [
        mocker.call.clone("https://x-access-token:foo@github.com/bar.wiki.git", "."),
        mocker.call.add("baz"),
        mocker.call.diff("--staged", "--exit-code"),
        mocker.call.config("user.email", "python-coverage-comment-action"),
        mocker.call.config("user.name", "python-coverage-comment-action"),
        mocker.call.commit("-m", "Update badge"),
        mocker.call.push("-u", "origin"),
    ]


def test_upload_file__no_change(mocker, get_logs):
    git = mocker.MagicMock()

    wiki.upload_file(
        github_token="foo",
        repository="bar",
        filename=pathlib.Path("baz"),
        contents="qux",
        git=git,
    )

    assert git.mock_calls == [
        mocker.call.clone("https://x-access-token:foo@github.com/bar.wiki.git", "."),
        mocker.call.add("baz"),
        mocker.call.diff("--staged", "--exit-code"),
    ]
    assert get_logs("INFO", "No change detected")


@pytest.mark.parametrize(
    "error_message, log_expected",
    [
        ("remote error: access denied or repository not exported", True),
        ("", False),
    ],
)
def test_upload_file__push_error(mocker, get_logs, error_message, log_expected):
    git = mocker.MagicMock()
    git.diff.side_effect = subprocess.GitError
    git.push.side_effect = subprocess.GitError(error_message)

    with pytest.raises(subprocess.GitError):
        wiki.upload_file(
            github_token="foo",
            repository="bar",
            filename=pathlib.Path("baz"),
            contents="qux",
            git=git,
        )

    logs = get_logs("ERROR", "Wiki seems not to be initialized for this project")
    assert bool(logs) is log_expected


def test_get_file_contents(session):
    session.register("GET", "https://raw.githubusercontent.com/wiki/foo/bar")(
        text="foo"
    )

    result = wiki.get_file_contents(session=session, repository="foo", filename="bar")
    assert result == "foo"


def test_get_file_contents__not_found(session, get_logs):
    session.register("GET", "https://raw.githubusercontent.com/wiki/foo/bar")(
        status_code=404
    )
    result = wiki.get_file_contents(session=session, repository="foo", filename="bar")
    assert result is None

    assert get_logs("WARNING", "Previous coverage results not found")


def test_get_file_contents_private_wiki(session):
    session.register("GET", "https://raw.githubusercontent.com/wiki/foo/bar")(
        status_code=404
    )

    with patch.object(subprocess, "Git", MockGit) as mock_git:
        result = wiki.get_file_contents(
            session=session,
            repository="foo",
            filename="bar",
            git=mock_git(),
            github_token="x",
        )

        assert result == "baz"


def test_get_file_contents_private_wiki__not_found(session):
    session.register("GET", "https://raw.githubusercontent.com/wiki/foo/rab")(
        status_code=404
    )

    with patch.object(subprocess, "Git", MockGit) as mock_git:
        result = wiki.get_file_contents(
            session=session,
            repository="foo",
            filename="rab",
            git=mock_git(),
            github_token="x",
        )

        assert result is None
