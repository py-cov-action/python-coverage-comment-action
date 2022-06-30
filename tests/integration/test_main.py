import os
import pathlib
import subprocess

import pytest

from coverage_comment import main
from coverage_comment import subprocess as coverage_subprocess


@pytest.fixture
def in_integration_env(integration_env, integration_dir):
    curdir = os.getcwd()
    os.chdir(integration_dir)
    yield integration_dir
    os.chdir(curdir)


@pytest.fixture
def integration_dir(tmpdir_factory):
    return tmpdir_factory.mktemp("integration_test")


@pytest.fixture
def file_path(integration_dir):
    return integration_dir / "foo.py"


@pytest.fixture
def write_file(file_path):
    def _(*variables):
        content = "import os"
        for i, var in enumerate(variables):
            content += f"""\nif os.environ.get("{var}"):\n    {i}\n"""
        file_path.write_text(content, encoding="utf8")

    return _


@pytest.fixture
def run_coverage(file_path, integration_dir):
    def _(*variables):
        subprocess.check_call(
            ["coverage", "run", "--parallel", file_path.basename],
            cwd=integration_dir,
            env=os.environ | dict.fromkeys(variables, "1"),
        )

    return _


@pytest.fixture
def integration_env(integration_dir, write_file, run_coverage):
    subprocess.check_call(["git", "init", "-b", "main"], cwd=integration_dir)
    # diff coverage reads the "origin/{...}" branch so we simulate an origin remote
    subprocess.check_call(["git", "remote", "add", "origin", "."], cwd=integration_dir)
    write_file("A", "B")

    subprocess.check_call(
        ["git", "add", "."],
        cwd=integration_dir,
    )
    subprocess.check_call(
        ["git", "commit", "-m", "commit"],
        cwd=integration_dir,
        env={
            "GIT_AUTHOR_NAME": "foo",
            "GIT_AUTHOR_EMAIL": "foo",
            "GIT_COMMITTER_NAME": "foo",
            "GIT_COMMITTER_EMAIL": "foo",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )
    subprocess.check_call(
        ["git", "switch", "-c", "branch"],
        cwd=integration_dir,
    )
    write_file("A", "B", "C")
    run_coverage("A", "C")
    subprocess.check_call(["git", "fetch", "origin"], cwd=integration_dir)


def test_action__pull_request__store_comment(
    pull_request_config, session, in_integration_env, capsys
):
    # No existing badge in this test
    session.register(
        "GET",
        "https://raw.githubusercontent.com/wiki/ewjoachim/foobar/python-coverage-comment-action-badge.json",
    )(status_code=404)

    # Who am I
    session.register("GET", "/user")(json={"login": "foo"})
    # Are there already comments
    session.register("GET", "/repos/ewjoachim/foobar/issues/2/comments")(json=[])

    comment = None

    def checker(payload):
        body = payload["body"]
        assert "## Coverage report" in body
        nonlocal comment
        comment = body
        return True

    # Post a new comment
    session.register("POST", "/repos/ewjoachim/foobar/issues/2/comments", json=checker)(
        status_code=403
    )

    result = main.action(
        config=pull_request_config(),
        github_session=session,
        http_session=session,
        git=None,
    )
    assert result == 0

    comment_file = pathlib.Path("python-coverage-comment-action.txt").read_text()
    assert comment == comment_file
    assert "The coverage rate is `86%`" in comment
    assert "`100%` of new lines are covered." in comment
    assert (
        "### foo.py\n`100%` of new lines are covered (`86%` of the complete file)"
        in comment
    )
    assert (
        "<!-- This comment was produced by python-coverage-comment-action -->"
        in comment
    )

    expected_stdout = "::set-output name=COMMENT_FILE_WRITTEN::true"
    assert capsys.readouterr().out.strip() == expected_stdout


def test_action__pull_request__post_comment(
    pull_request_config, session, in_integration_env, capsys
):
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "https://raw.githubusercontent.com/wiki/ewjoachim/foobar/python-coverage-comment-action-badge.json",
    )(json={"message": "30%"})

    # Who am I
    session.register("GET", "/user")(json={"login": "foo"})
    # Are there already comments
    session.register("GET", "/repos/ewjoachim/foobar/issues/2/comments")(json=[])

    comment = None

    def checker(payload):
        body = payload["body"]
        assert "## Coverage report" in body
        nonlocal comment
        comment = body
        return True

    # Post a new comment
    session.register(
        "POST",
        "/repos/ewjoachim/foobar/issues/2/comments",
        json=checker,
    )(
        status_code=200,
    )

    result = main.action(
        config=pull_request_config(),
        github_session=session,
        http_session=session,
        git=None,
    )
    assert result == 0

    assert not pathlib.Path("python-coverage-comment-action.txt").exists()
    assert "The coverage rate went from `30%` to `86%` :arrow_up:" in comment

    expected_stdout = "::set-output name=COMMENT_FILE_WRITTEN::false"
    assert capsys.readouterr().out.strip() == expected_stdout


def test_action__push__non_default_branch(
    push_config, session, in_integration_env, get_logs
):
    session.register("GET", "/repos/ewjoachim/foobar")(json={"default_branch": "main"})

    result = main.action(
        config=push_config(GITHUB_REF="refs/heads/master"),
        github_session=session,
        http_session=session,
        git=None,
    )
    assert result == 0

    assert get_logs("INFO", "Skipping badge")


def test_action__push__default_branch(
    push_config, session, in_integration_env, get_logs
):
    session.register("GET", "/repos/ewjoachim/foobar")(json={"default_branch": "main"})

    class Git(coverage_subprocess.Git):
        clone_args = None
        push_args = None
        pushed_file = None

        def clone(self, *args):
            self.clone_args = list(args)
            subprocess.check_call(["git", "init"], cwd=self.cwd)

        def push(self, *args):
            self.push_args = list(args)
            subprocess.check_call(["git", "diff", "--exit-code"], cwd=self.cwd)

            self.pushed_file = pathlib.Path(
                self.cwd, "python-coverage-comment-action-badge.json"
            ).read_text()

    git = Git()

    result = main.action(
        config=push_config(),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    assert not get_logs("INFO", "Skipping badge")
    assert get_logs("INFO", "Saving Badge into the repo wiki")
    url = "https://raw.githubusercontent.com/wiki/ewjoachim/foobar/python-coverage-comment-action-badge.json"
    assert get_logs("INFO", f"Badge JSON stored at {url}")
    assert get_logs("INFO", f"Badge URL: https://img.shields.io/endpoint?url={url}")

    assert git.clone_args == [
        "https://x-access-token:foo@github.com/ewjoachim/foobar.wiki.git",
        ".",
    ]
    assert git.push_args == ["-u", "origin"]

    badge = """{"schemaVersion": 1, "label": "Coverage", "message": "85%", "color": "orange"}"""
    assert git.pushed_file == badge


def test_action__workflow_run__no_pr(
    workflow_run_config, session, in_integration_env, get_logs
):
    session.register("GET", "/user")(json={"login": "foo"})
    session.register("GET", "/repos/ewjoachim/foobar/actions/runs/123")(
        json={"head_branch": "branch", "head_repository": {"owner": {"login": "bar"}}}
    )

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/pulls",
        params={
            "head": "bar:branch",
            "sort": "updated",
            "direction": "desc",
            "state": "open",
        },
    )(json=[])
    session.register(
        "GET",
        "/repos/ewjoachim/foobar/pulls",
        params={
            "head": "bar:branch",
            "sort": "updated",
            "direction": "desc",
            "state": "all",
        },
    )(json=[])

    result = main.action(
        config=workflow_run_config(),
        github_session=session,
        http_session=session,
        git=None,
    )

    assert result == 1
    assert get_logs("ERROR", "The PR cannot be found")


def test_action__workflow_run__no_artifact(
    workflow_run_config, session, in_integration_env, get_logs
):
    session.register("GET", "/user")(json={"login": "foo"})
    session.register("GET", "/repos/ewjoachim/foobar/actions/runs/123")(
        json={"head_branch": "branch", "head_repository": {"owner": {"login": "bar"}}}
    )

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/pulls",
        params={
            "head": "bar:branch",
            "sort": "updated",
            "direction": "desc",
            "state": "open",
        },
    )(json=[{"number": 456}])

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/actions/runs/123/artifacts",
    )(json={"artifacts": [{"name": "wrong_name"}]})

    result = main.action(
        config=workflow_run_config(),
        github_session=session,
        http_session=session,
        git=None,
    )

    assert result == 0
    assert get_logs("INFO", "Artifact was not found")


def test_action__workflow_run__post_comment(
    workflow_run_config, session, in_integration_env, get_logs, zip_bytes
):
    session.register("GET", "/user")(json={"login": "foo"})
    session.register("GET", "/repos/ewjoachim/foobar/actions/runs/123")(
        json={"head_branch": "branch", "head_repository": {"owner": {"login": "bar"}}}
    )

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/pulls",
        params={
            "head": "bar:branch",
            "sort": "updated",
            "direction": "desc",
            "state": "open",
        },
    )(json=[{"number": 456}])

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/actions/runs/123/artifacts",
    )(json={"artifacts": [{"name": "python-coverage-comment-action", "id": 789}]})

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/actions/artifacts/789/zip",
    )(content=zip_bytes(filename="python-coverage-comment-action.txt", content="Hey!"))

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/issues/456/comments",
    )(json=[])

    session.register(
        "POST",
        "/repos/ewjoachim/foobar/issues/456/comments",
        json={"body": "Hey!"},
    )()

    result = main.action(
        config=workflow_run_config(),
        github_session=session,
        http_session=session,
        git=None,
    )

    assert result == 0
    assert get_logs("INFO", "Comment file found in artifact, posting to PR")
    assert get_logs("INFO", "Comment posted in PR")
