from __future__ import annotations

import pathlib

import pytest

from coverage_comment import files, storage, subprocess


def test_checked_out_branch(git):
    git.register("git branch --show-current")(stdout="bar")
    git.register("git reset --hard")()
    git.register("git fetch origin foo")()
    git.register("git switch foo")()

    with storage.checked_out_branch(git=git, branch="foo"):
        git.register("git switch bar")()


def test_checked_out_branch__detached_head(git):
    git.register("git branch --show-current")(stdout="")
    git.register("git rev-parse --short HEAD")(stdout="123abc")
    git.register("git reset --hard")()
    git.register("git fetch origin foo")()
    git.register("git switch foo")()

    with storage.checked_out_branch(git=git, branch="foo"):
        git.register("git switch --detach 123abc")()


def test_checked_out_branch__branch_does_not_exist(git):
    git.register("git branch --show-current")(stdout="bar")
    git.register("git reset --hard")()
    git.register("git fetch origin foo")(exit_code=1)
    git.register("git fetch origin")()
    git.register("git rev-parse --verify origin/foo")(exit_code=1)
    git.register("git switch --orphan foo")()

    with storage.checked_out_branch(git=git, branch="foo"):
        git.register("git switch bar")()


def test_checked_out_branch__fetch_fails(git):
    git.register("git branch --show-current")(stdout="bar")
    git.register("git reset --hard")()
    git.register("git fetch origin foo")(exit_code=1)
    git.register("git fetch origin")()
    git.register("git rev-parse --verify origin/foo")()

    with pytest.raises(subprocess.GitError):
        with storage.checked_out_branch(git=git, branch="foo"):
            pass


def test_commit_operations__no_diff(git, in_tmp_path):
    operations = [
        files.WriteFile(path=pathlib.Path("a.txt"), contents="a"),
        files.WriteFile(path=pathlib.Path("b.txt"), contents="b"),
    ]

    # checked_out_branch
    git.register("git branch --show-current")(stdout="bar")
    git.register("git reset --hard")()
    git.register("git fetch origin foo")()
    git.register("git switch foo")()

    # upload_files
    git.register(f"git add {operations[0].path}")()
    git.register(f"git add {operations[1].path}")()
    git.register("git diff --staged --exit-code")()  # no diff

    # __exit__ of checked_out_branch
    git.register("git switch bar")()

    storage.commit_operations(
        operations=operations,
        git=git,
        branch="foo",
    )

    # But content has been written to disk
    assert operations[0].path.read_text() == operations[0].contents
    assert operations[1].path.read_text() == operations[1].contents


def test_commit_operations(git, in_tmp_path):
    operations = [
        files.WriteFile(path=pathlib.Path("a.txt"), contents="a"),
        files.WriteFile(path=pathlib.Path("b.txt"), contents="b"),
    ]

    # checked_out_branch
    git.register("git branch --show-current")(stdout="bar")
    git.register("git reset --hard")()
    git.register("git fetch origin foo")()
    git.register("git switch foo")()

    # upload_files
    git.register(f"git add {operations[0].path}")()
    git.register(f"git add {operations[1].path}")()

    git.register("git diff --staged --exit-code")(exit_code=1)  # diff!

    # (yes, it's missing the quotes, but this is just an artifact from our test
    # double)
    git.register(
        "git commit --message Update coverage data",
        env={
            "GIT_AUTHOR_NAME": "github-actions",
            "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
            "GIT_COMMITTER_NAME": "github-actions",
            "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
        },
    )()
    git.register("git push origin foo")()

    # __exit__ of checked_out_branch
    git.register("git switch bar")()

    storage.commit_operations(
        operations=operations,
        git=git,
        branch="foo",
    )

    assert operations[0].path.read_text() == operations[0].contents
    assert operations[1].path.read_text() == operations[1].contents


def test_get_datafile_contents__not_found(gh, session):
    session.register("GET", "/repos/foo/bar/contents/data.json", params={"ref": "baz"})(
        status_code=404
    )

    result = storage.get_datafile_contents(
        github=gh,
        repository="foo/bar",
        branch="baz",
    )
    assert result is None


def test_get_datafile_contents(gh, session):
    session.register("GET", "/repos/foo/bar/contents/data.json", params={"ref": "baz"})(
        text="yay", headers={"content-type": "application/vnd.github.raw+json"}
    )

    result = storage.get_datafile_contents(
        github=gh,
        repository="foo/bar",
        branch="baz",
    )
    assert result == "yay"


@pytest.mark.parametrize(
    "github_host, is_public, expected",
    [
        ("https://github.com", False, "https://github.com/foo/bar/raw/baz/qux"),
        ("https://github.com", True, "https://raw.githubusercontent.com/foo/bar/baz/qux"),
        ("https://github.mycompany.com", True, "https://github.mycompany.com/foo/bar/raw/baz/qux"),
    ],
)
def test_get_raw_file_url(github_host, is_public, expected):
    result = storage.get_raw_file_url(
        github_host=github_host,
        repository="foo/bar",
        branch="baz",
        path=pathlib.Path("qux"),
        is_public=is_public,
    )
    assert result == expected


@pytest.mark.parametrize(
    "github_host, path, expected",
    [
        ("https://github.com", "", "https://github.com/foo/bar/tree/baz"),
        ("https://github.com", "/", "https://github.com/foo/bar/tree/baz"),
        ("https://github.com", "qux", "https://github.com/foo/bar/blob/baz/qux"),  # blob
        ("https://github.com", "qux/", "https://github.com/foo/bar/tree/baz/qux"),
        ("https://github.mycompany.com", "/qux", "https://github.mycompany.com/foo/bar/blob/baz/qux"),  # blob
        ("https://github.mycompany.com", "/qux/", "https://github.mycompany.com/foo/bar/tree/baz/qux"),
    ],
)
def test_get_repo_file_url(github_host, path, expected):
    result = storage.get_repo_file_url(github_host=github_host, repository="foo/bar", branch="baz", path=path)

    assert result == expected

@pytest.mark.parametrize(
    "github_host",
    [
        "https://github.com",
        "https://github.mycompany.com",
    ],
)
def test_get_repo_file_url__no_path(github_host):
    result = storage.get_repo_file_url(github_host=github_host, repository="foo/bar", branch="baz")

    assert result == f"{github_host}/foo/bar/tree/baz"

@pytest.mark.parametrize(
    "github_host, expected",
    [
        ("https://github.com", "https://htmlpreview.github.io/?https://github.com/foo/bar/blob/baz/htmlcov/index.html"),
        ("https://github.mycompany.com", "https://github.mycompany.com/foo/bar/blob/baz/htmlcov/index.html"),
    ],
)
def test_get_html_report_url(github_host, expected):
    result = storage.get_html_report_url(github_host=github_host, repository="foo/bar", branch="baz")
    assert result == expected
