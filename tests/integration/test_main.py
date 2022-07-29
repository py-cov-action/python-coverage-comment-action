import base64
import json
import os
import pathlib
import subprocess

import pytest

from coverage_comment import main


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
        "/repos/ewjoachim/foobar/contents/data.json",
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
    payload = json.dumps({"coverage": 30.00})
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "/repos/ewjoachim/foobar/contents/data.json",
    )(json={"content": base64.b64encode(payload.encode()).decode()})

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


def test_action__pull_request__force_store_comment(
    pull_request_config, session, in_integration_env, capsys
):
    payload = json.dumps({"coverage": 30.00})
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "/repos/ewjoachim/foobar/contents/data.json",
    )(json={"content": base64.b64encode(payload.encode()).decode()})

    result = main.action(
        config=pull_request_config(FORCE_WORKFLOW_RUN=True),
        github_session=session,
        http_session=session,
        git=None,
    )
    assert result == 0

    assert pathlib.Path("python-coverage-comment-action.txt").exists()

    expected_stdout = "::set-output name=COMMENT_FILE_WRITTEN::true"
    assert capsys.readouterr().out.strip() == expected_stdout


def test_action__pull_request__post_comment__no_marker(
    pull_request_config, session, in_integration_env, get_logs
):
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "/repos/ewjoachim/foobar/contents/data.json",
    )(status_code=404)

    result = main.action(
        config=pull_request_config(COMMENT_TEMPLATE="""foo"""),
        github_session=session,
        http_session=session,
        git=None,
    )
    assert result == 1
    assert get_logs("ERROR", "Marker not found")


def test_action__pull_request__post_comment__template_error(
    pull_request_config, session, in_integration_env, get_logs
):
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "/repos/ewjoachim/foobar/contents/data.json",
    )(status_code=404)

    result = main.action(
        config=pull_request_config(COMMENT_TEMPLATE="""{%"""),
        github_session=session,
        http_session=session,
        git=None,
    )
    assert result == 1
    assert get_logs("ERROR", "There was a rendering error")


def test_action__push__non_default_branch(
    push_config, session, in_integration_env, get_logs
):
    session.register("GET", "/repos/ewjoachim/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )

    result = main.action(
        config=push_config(GITHUB_REF="refs/heads/master"),
        github_session=session,
        http_session=session,
        git=None,
    )
    assert result == 0

    assert get_logs("INFO", "Skipping badge")


def test_action__push__default_branch(
    push_config, session, in_integration_env, get_logs, git
):
    session.register("GET", "/repos/ewjoachim/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    session.register(
        "GET",
        "https://img.shields.io/static/v1?label=Coverage&message=85%25&color=orange",
    )(text="<this is a svg badge>")

    git.register("git branch --show-current")(stdout="foo")
    git.register("git fetch")()
    git.register("git checkout python-coverage-comment-action-data")()
    git.register("git add endpoint.json")()
    git.register("git add data.json")()
    git.register("git add badge.svg")()
    git.register("git diff --staged --exit-code")(exit_code=1)
    git.register("git commit --message Update badge")()
    git.register("git push origin")()
    git.register("git checkout foo")()

    result = main.action(
        config=push_config(),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    assert not get_logs("INFO", "Skipping badge")
    assert get_logs("INFO", "Saving coverage files & badge into the repository")

    log = get_logs("INFO", "Badge SVG available at")[0]
    expected = """You can use the following URLs to display your badge:

Badge SVG available at:
    https://raw.githubusercontent.com/ewjoachim/foobar/python-coverage-comment-action-data/badge.svg

Badge from shields endpoint is easier to customize but doesn't work with private repo:
    https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/ewjoachim/foobar/python-coverage-comment-action-data/endpoint.json

Badge from shields dynamic url (less useful but you never know):
    https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fewjoachim%2Ffoobar%2Fpython-coverage-comment-action-data%2Fendpoint.json

See more details and ready-to-copy-paste-markdown at https://github.com/ewjoachim/foobar/tree/python-coverage-comment-action-data"""
    assert log == expected


def test_action__workflow_run__no_pr(
    workflow_run_config, session, in_integration_env, get_logs
):
    session.register("GET", "/user")(json={"login": "foo"})
    session.register("GET", "/repos/ewjoachim/foobar/actions/runs/123")(
        json={
            "head_branch": "branch",
            "head_repository": {"full_name": "bar/repo-name"},
        }
    )

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/pulls",
        params={
            "head": "bar/repo-name:branch",
            "sort": "updated",
            "direction": "desc",
            "state": "open",
        },
    )(json=[])
    session.register(
        "GET",
        "/repos/ewjoachim/foobar/pulls",
        params={
            "head": "bar/repo-name:branch",
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
        json={
            "head_branch": "branch",
            "head_repository": {"full_name": "bar/repo-name"},
        }
    )

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/pulls",
        params={
            "head": "bar/repo-name:branch",
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
        json={
            "head_branch": "branch",
            "head_repository": {"full_name": "bar/repo-name"},
        }
    )

    session.register(
        "GET",
        "/repos/ewjoachim/foobar/pulls",
        params={
            "head": "bar/repo-name:branch",
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
