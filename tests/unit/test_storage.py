from __future__ import annotations

import pathlib

import pytest

from coverage_comment import files, storage, subprocess


def test_checked_out_branch(git):
    git.register("branch --show-current", stdout="bar")
    git.register("reset --hard")
    git.register("--config-env=http.extraheader=GIT_EXTRA_HEADER fetch origin foo")
    git.register("switch foo")

    with storage.checked_out_branch(git=git, branch="foo", token="secret"):
        git.register("switch bar")


def test_checked_out_branch__detached_head(git):
    git.register("branch --show-current", stdout="")
    git.register("rev-parse --short HEAD", stdout="123abc")
    git.register("reset --hard")
    git.register("--config-env=http.extraheader=GIT_EXTRA_HEADER fetch origin foo")
    git.register("switch foo")

    with storage.checked_out_branch(git=git, branch="foo", token="secret"):
        git.register("switch --detach 123abc")


def test_checked_out_branch__branch_does_not_exist(git):
    git.register("branch --show-current", stdout="bar")
    git.register("reset --hard")
    git.register(
        "--config-env=http.extraheader=GIT_EXTRA_HEADER fetch origin foo",
        returncode=1,
    )
    git.register("--config-env=http.extraheader=GIT_EXTRA_HEADER fetch origin")
    git.register("rev-parse --verify origin/foo", returncode=1)
    git.register("switch --orphan foo")

    with storage.checked_out_branch(git=git, branch="foo", token="secret"):
        git.register("switch bar")


def test_checked_out_branch__fetch_fails(git):
    git.register("branch --show-current", stdout="bar")
    git.register("reset --hard")
    git.register(
        "--config-env=http.extraheader=GIT_EXTRA_HEADER fetch origin foo",
        returncode=1,
    )
    git.register("--config-env=http.extraheader=GIT_EXTRA_HEADER fetch origin")
    git.register("rev-parse --verify origin/foo")

    with pytest.raises(subprocess.GitError):
        with storage.checked_out_branch(git=git, branch="foo", token="secret"):
            pass


def test_commit_operations__no_diff(git, in_tmp_path):
    operations = [
        files.WriteFile(path=pathlib.Path("a.txt"), contents="a"),
        files.WriteFile(path=pathlib.Path("b.txt"), contents="b"),
    ]

    # checked_out_branch
    git.register("branch --show-current", stdout="bar")
    git.register("reset --hard")
    git.register("--config-env=http.extraheader=GIT_EXTRA_HEADER fetch origin foo")
    git.register("switch foo")

    # upload_files
    git.register(f"add {operations[0].path}")
    git.register(f"add {operations[1].path}")
    git.register("diff --staged --exit-code")  # no diff

    # __exit__ of checked_out_branch
    git.register("switch bar")

    storage.commit_operations(
        operations=operations,
        git=git,
        branch="foo",
        token="secret",
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
    git.register("branch --show-current", stdout="bar")
    git.register("reset --hard")
    git.register("--config-env=http.extraheader=GIT_EXTRA_HEADER fetch origin foo")
    git.register("switch foo")

    # upload_files
    git.register(f"add {operations[0].path}")
    git.register(f"add {operations[1].path}")

    git.register("diff --staged --exit-code", returncode=1)  # diff!

    # (yes, it's missing the quotes, but this is just an artifact from our test
    # double)
    registered = git.register("commit --message 'ci: Update coverage data'")
    git.register("--config-env=http.extraheader=GIT_EXTRA_HEADER push origin foo")

    # __exit__ of checked_out_branch
    git.register("switch bar")

    storage.commit_operations(
        operations=operations,
        git=git,
        branch="foo",
        token="secret",
    )

    assert operations[0].path.read_text() == operations[0].contents
    assert operations[1].path.read_text() == operations[1].contents
    assert registered.calls[0].kwargs["env"]["GIT_AUTHOR_NAME"] == "github-actions"
    assert (
        registered.calls[0].kwargs["env"]["GIT_AUTHOR_EMAIL"]
        == "41898282+github-actions[bot]@users.noreply.github.com"
    )
    assert registered.calls[0].kwargs["env"]["GIT_COMMITTER_NAME"] == "github-actions"
    assert (
        registered.calls[0].kwargs["env"]["GIT_COMMITTER_EMAIL"]
        == "41898282+github-actions[bot]@users.noreply.github.com"
    )


def test_get_datafile_contents__not_found(gh, session):
    session.register(
        "GET",
        "/repos/foo/bar/contents/data.json",
        match_params={"ref": "baz"},
        status_code=404,
    )

    result = storage.get_datafile_contents(
        github=gh,
        repository="foo/bar",
        branch="baz",
    )
    assert result is None


def test_get_datafile_contents(gh, session):
    session.register(
        "GET",
        "/repos/foo/bar/contents/data.json",
        match_params={"ref": "baz"},
        text="yay",
        headers={"content-type": "application/vnd.github.raw+json"},
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
        (
            "https://github.com",
            True,
            "https://raw.githubusercontent.com/foo/bar/baz/qux",
        ),
        (
            "https://github.mycompany.com",
            True,
            "https://github.mycompany.com/foo/bar/raw/baz/qux",
        ),
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
        (
            "https://github.com",
            "qux",
            "https://github.com/foo/bar/blob/baz/qux",
        ),  # blob
        ("https://github.com", "qux/", "https://github.com/foo/bar/tree/baz/qux"),
        (
            "https://github.mycompany.com",
            "/qux",
            "https://github.mycompany.com/foo/bar/blob/baz/qux",
        ),  # blob
        (
            "https://github.mycompany.com",
            "/qux/",
            "https://github.mycompany.com/foo/bar/tree/baz/qux",
        ),
    ],
)
def test_get_repo_file_url(github_host, path, expected):
    result = storage.get_repo_file_url(
        github_host=github_host, repository="foo/bar", branch="baz", path=path
    )

    assert result == expected


@pytest.mark.parametrize(
    "github_host",
    [
        "https://github.com",
        "https://github.mycompany.com",
    ],
)
def test_get_repo_file_url__no_path(github_host):
    result = storage.get_repo_file_url(
        github_host=github_host, repository="foo/bar", branch="baz"
    )

    assert result == f"{github_host}/foo/bar/tree/baz"


@pytest.mark.parametrize(
    "github_host,use_gh_pages_html_url,expected",
    [
        (
            "https://github.com",
            True,
            "https://foo.github.io/bar/htmlcov/index.html",
        ),
        (
            "https://github.com",
            False,
            "https://htmlpreview.github.io/?https://github.com/foo/bar/blob/baz/htmlcov/index.html",
        ),
        (
            "https://github.mycompany.com",
            True,
            "https://github.mycompany.com/pages/foo/bar/htmlcov/index.html",
        ),
        (
            "https://github.mycompany.com",
            False,
            "https://github.mycompany.com/foo/bar/blob/baz/htmlcov/index.html",
        ),
    ],
)
def test_get_html_report_url(github_host, use_gh_pages_html_url, expected):
    result = storage.get_html_report_url(
        github_host=github_host,
        repository="foo/bar",
        branch="baz",
        use_gh_pages_html_url=use_gh_pages_html_url,
    )
    assert result == expected
