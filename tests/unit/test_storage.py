import base64
import pathlib

import pytest

from coverage_comment import files, storage


def test_switch_to_branch(git):
    git.register("git branch --show-current")(stdout="bar")
    git.register("git fetch")()
    git.register("git reset --hard")()
    git.register("git rev-parse --verify foo")()
    git.register("git switch foo")()

    with storage.switch_to_branch(git=git, branch="foo"):
        git.register("git switch bar")()


def test_switch_to_branch__detached_head(git):
    git.register("git branch --show-current")(exit_code=1)
    git.register("git rev-parse --short HEAD")(stdout="123abc")
    git.register("git fetch")()
    git.register("git reset --hard")()
    git.register("git rev-parse --verify foo")()
    git.register("git switch foo")()

    with storage.switch_to_branch(git=git, branch="foo"):
        git.register("git switch 123abc")()


def test_switch_to_branch__branch_doesnt_exist(git):
    git.register("git branch --show-current")(stdout="bar")
    git.register("git fetch")()
    git.register("git reset --hard")()
    git.register("git rev-parse --verify foo")(exit_code=1)
    git.register("git switch --orphan foo")()

    with storage.switch_to_branch(git=git, branch="foo"):
        git.register("git switch bar")()


def test_commit_operations__no_diff(git, in_tmp_path):
    operations = [
        files.WriteFile(path=pathlib.Path("a.txt"), contents="a"),
        files.WriteFile(path=pathlib.Path("b.txt"), contents="b"),
    ]

    # switch_to_branch
    git.register("git branch --show-current")(stdout="bar")
    git.register("git fetch")()
    git.register("git reset --hard")()
    git.register("git rev-parse --verify foo")()
    git.register("git switch foo")()

    # upload_files
    git.register(f"git add {operations[0].path}")()
    git.register(f"git add {operations[1].path}")()
    git.register("git diff --staged --exit-code")()  # no diff

    # __exit__ of switch_to_branch
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

    # switch_to_branch
    git.register("git branch --show-current")(stdout="bar")
    git.register("git fetch")()
    git.register("git reset --hard")()
    git.register("git rev-parse --verify foo")()
    git.register("git switch foo")()

    # upload_files
    git.register(f"git add {operations[0].path}")()
    git.register(f"git add {operations[1].path}")()

    git.register("git diff --staged --exit-code")(exit_code=1)  # diff!

    # (yes, it's missing the quotes, but this is just an artifact from our test
    # double)
    git.register(
        "git commit --message Update badge",
        env={
            "GIT_AUTHOR_NAME": "github-actions",
            "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
            "GIT_COMMITTER_NAME": "github-actions",
            "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
        },
    )()
    git.register("git push origin foo")()

    # __exit__ of switch_to_branch
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
    payload = base64.b64encode(b"yay").decode()
    session.register("GET", "/repos/foo/bar/contents/data.json", params={"ref": "baz"})(
        json={"content": payload}
    )

    result = storage.get_datafile_contents(
        github=gh,
        repository="foo/bar",
        branch="baz",
    )
    assert result == "yay"


@pytest.mark.parametrize(
    "is_public, expected",
    [
        (False, "https://github.com/foo/bar/raw/baz/qux"),
        (True, "https://raw.githubusercontent.com/foo/bar/baz/qux"),
    ],
)
def test_get_raw_file_url(is_public, expected):
    result = storage.get_raw_file_url(
        repository="foo/bar",
        branch="baz",
        path=pathlib.Path("qux"),
        is_public=is_public,
    )
    assert result == expected


@pytest.mark.parametrize(
    "path, expected",
    [
        ("", "https://github.com/foo/bar/tree/baz"),
        ("/", "https://github.com/foo/bar/tree/baz"),
        ("qux", "https://github.com/foo/bar/blob/baz/qux"),  # blob
        ("qux/", "https://github.com/foo/bar/tree/baz/qux"),
        ("/qux", "https://github.com/foo/bar/blob/baz/qux"),  # blob
        ("/qux/", "https://github.com/foo/bar/tree/baz/qux"),
    ],
)
def test_get_repo_file_url(path, expected):
    result = storage.get_repo_file_url(repository="foo/bar", branch="baz", path=path)

    assert result == expected


def test_get_repo_file_url__no_path():
    result = storage.get_repo_file_url(repository="foo/bar", branch="baz")

    assert result == "https://github.com/foo/bar/tree/baz"


def test_get_html_report_url():
    result = storage.get_html_report_url(repository="foo/bar", branch="baz")
    expected = "https://htmlpreview.github.io/?https://github.com/foo/bar/blob/baz/htmlcov/index.html"
    assert result == expected
