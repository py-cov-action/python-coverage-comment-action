import base64
import pathlib

import pytest

from coverage_comment import files, storage


def test_initialize_branch(git, tmp_path):

    readme_path = tmp_path / "readme.txt"
    git.register("git checkout --orphan foo")()
    git.register("git reset --hard")()
    git.register(f"git add {readme_path}")()
    git.register(
        "git commit --message Initialize python-coverage-comment-action special branch",
        env={
            "GIT_AUTHOR_NAME": "github-actions",
            "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
            "GIT_COMMITTER_NAME": "github-actions",
            "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
        },
    )()

    storage.initialize_branch(
        git=git,
        branch="foo",
        initial_file=files.FileWithPath(path=readme_path, contents="bar"),
    )

    assert readme_path.read_text() == "bar"


def test_on_coverage_branch(git):

    git.register("git branch --show-current")(stdout="bar")
    git.register("git fetch")()
    git.register("git checkout foo")()

    with storage.on_coverage_branch(git=git, branch="foo") as exists:
        assert exists is True
        git.register("git checkout bar")()


def test_on_coverage_branch__detached_head(git):

    git.register("git branch --show-current")(exit_code=1)
    git.register("git rev-parse --short HEAD")(stdout="123abc")
    git.register("git fetch")()
    git.register("git checkout foo")()

    with storage.on_coverage_branch(git=git, branch="foo") as exists:
        assert exists is True
        git.register("git checkout 123abc")()


def test_on_coverage_branch__branch_doesnt_exist(git):

    git.register("git branch --show-current")(stdout="bar")
    git.register("git fetch")()
    git.register("git checkout foo")(exit_code=1)

    with storage.on_coverage_branch(git=git, branch="foo") as exists:
        assert exists is False
        git.register("git checkout bar")()


@pytest.mark.parametrize(
    "branch_exists, has_diff",
    [
        (False, True),
        (True, False),
    ],
)
def test_upload_files(git, in_tmp_path, branch_exists, has_diff):

    readme_path = pathlib.Path("readme.txt")
    initial_file = files.FileWithPath(path=readme_path, contents="foo")
    files_to_save = [
        files.FileWithPath(path=pathlib.Path("a.txt"), contents="a"),
        files.FileWithPath(path=pathlib.Path("b.txt"), contents="b"),
    ]

    # on_coverage_branch
    git.register("git branch --show-current")(stdout="bar")
    git.register("git fetch")()
    git.register("git checkout foo")(exit_code=0 if branch_exists else 1)

    # I usually hate `if` statements in tests, but we're doing
    # 2 different very repetitive (almost identical) tests here,
    # so it really just is a way to make it easier to maintain.
    # Let's not abuse it.
    if not branch_exists:
        # initialize_branch
        git.register("git checkout --orphan foo")()
        git.register("git reset --hard")()
        git.register(f"git add {readme_path}")()
        git.register(
            "git commit --message Initialize python-coverage-comment-action special branch",
            env={
                "GIT_AUTHOR_NAME": "github-actions",
                "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
                "GIT_COMMITTER_NAME": "github-actions",
                "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
            },
        )()

    # upload_files
    git.register(f"git add {files_to_save[0].path}")()
    git.register(f"git add {files_to_save[1].path}")()
    git.register("git diff --staged --exit-code")(exit_code=1 if has_diff else 0)

    if has_diff:
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

    # __exit__ of on_coverage_branch
    git.register("git checkout bar")()

    storage.upload_files(
        files=files_to_save,
        git=git,
        branch="foo",
        initial_file=initial_file,
    )

    assert files_to_save[0].path.read_text() == files_to_save[0].contents
    assert files_to_save[1].path.read_text() == files_to_save[1].contents


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
def test_get_file_url(is_public, expected):
    result = storage.get_file_url(
        repository="foo/bar",
        branch="baz",
        path=pathlib.Path("qux"),
        is_public=is_public,
    )
    assert result == expected


def test_get_readme_url():

    result = storage.get_readme_url(repository="foo/bar", branch="baz")

    assert result == "https://github.com/foo/bar/tree/baz"
