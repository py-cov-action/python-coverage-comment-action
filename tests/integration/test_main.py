from __future__ import annotations

import json
import os
import pathlib
import subprocess
import uuid

import pytest

from coverage_comment import main


@pytest.fixture
def in_integration_env(integration_env, integration_dir):
    curdir = os.getcwd()
    os.chdir(integration_dir)
    yield integration_dir
    os.chdir(curdir)


@pytest.fixture
def integration_dir(tmp_path: pathlib.Path):
    test_dir = tmp_path / "integration_test"
    test_dir.mkdir()
    return test_dir


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
            ["coverage", "run", "--parallel", file_path.name],
            cwd=integration_dir,
            env=os.environ | dict.fromkeys(variables, "1"),
        )

    return _


DIFF_STDOUT = """diff --git a/foo.py b/foo.py
index 6c08c94..b65c612 100644
--- a/foo.py
+++ b/foo.py
@@ -6,0 +7,6 @@ if os.environ.get("B"):
+
+if os.environ.get("C"):
+    2
+
+if os.environ.get("D"):
+    3
"""


@pytest.fixture
def commit(integration_dir):
    def _():
        subprocess.check_call(
            ["git", "add", "."],
            cwd=integration_dir,
        )
        subprocess.check_call(
            ["git", "commit", "-m", str(uuid.uuid4())],
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

    return _


@pytest.fixture
def integration_env(integration_dir, write_file, run_coverage, commit, request):
    subprocess.check_call(["git", "init", "-b", "main"], cwd=integration_dir)
    # diff coverage reads the "origin/{...}" branch so we simulate an origin remote
    subprocess.check_call(["git", "remote", "add", "origin", "."], cwd=integration_dir)
    write_file("A", "B")
    commit()

    add_branch_mark = request.node.get_closest_marker("add_branches")
    for additional_branch in add_branch_mark.args if add_branch_mark else []:
        subprocess.check_call(
            ["git", "switch", "-c", additional_branch],
            cwd=integration_dir,
        )

    subprocess.check_call(
        ["git", "switch", "-c", "branch"],
        cwd=integration_dir,
    )

    write_file("A", "B", "C", "D")
    commit()

    run_coverage("A", "C")
    subprocess.check_call(["git", "fetch", "origin"], cwd=integration_dir)


def test_action__invalid_event_name(session, push_config, in_integration_env, get_logs):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )

    result = main.action(
        config=push_config(GITHUB_EVENT_NAME="pull_request_target"),
        github_session=session,
        http_session=session,
        git=None,
    )

    assert result == 1
    assert get_logs("ERROR", "This action has only been designed to work for")


def test_action__pull_request__store_comment(
    pull_request_config,
    session,
    in_integration_env,
    output_file,
    summary_file,
    capsys,
    git,
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    # No existing badge in this test
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(status_code=404)

    # Who am I
    session.register("GET", "/user")(json={"login": "foo"})
    # Are there already comments
    session.register("GET", "/repos/py-cov-action/foobar/issues/2/comments")(json=[])

    comment = None

    def checker(payload):
        body = payload["body"]
        assert "## Coverage report" in body
        nonlocal comment
        comment = body
        return True

    # Post a new comment
    session.register(
        "POST", "/repos/py-cov-action/foobar/issues/2/comments", json=checker
    )(status_code=403)

    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

    result = main.action(
        config=pull_request_config(
            GITHUB_OUTPUT=output_file, GITHUB_STEP_SUMMARY=summary_file
        ),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    # Check that no annotations were made
    output = capsys.readouterr()
    assert output.err.strip() == ""

    comment_file = pathlib.Path("python-coverage-comment-action.txt").read_text()
    assert comment == comment_file
    assert comment == summary_file.read_text()
    assert (
        "Coverage for the whole project is 77.77%. Previous coverage rate is not available"
        in comment
    )
    assert (
        "In this PR, 4 new statements are added to the whole project, 3 of which are covered (75%)."
        in comment
    )
    assert (
        "https://github.com/py-cov-action/foobar/pull/2/files#diff-b08fd7a517303ab07cfa211f74d03c1a4c2e64b3b0656d84ff32ecb449b785d2"
        in comment
    )
    assert (
        "<!-- This comment was produced by python-coverage-comment-action -->"
        in comment
    )

    expected_output = "COMMENT_FILE_WRITTEN=true\n"

    assert output_file.read_text() == expected_output


@pytest.mark.add_branches("foo")
def test_action__pull_request__store_comment_not_targeting_default(
    pull_request_config,
    session,
    in_integration_env,
    output_file,
    summary_file,
    capsys,
    git,
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    payload = json.dumps({"coverage": 30.00})

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(text=payload, headers={"content-type": "application/vnd.github.raw+json"})

    # Who am I
    session.register("GET", "/user")(json={"login": "foo"})
    # Are there already comments
    session.register("GET", "/repos/py-cov-action/foobar/issues/2/comments")(json=[])

    comment = None

    def checker(payload):
        body = payload["body"]
        assert "## Coverage report" in body
        nonlocal comment
        comment = body
        return True

    # Post a new comment
    session.register(
        "POST", "/repos/py-cov-action/foobar/issues/2/comments", json=checker
    )(status_code=403)

    git.register("git fetch origin foo --depth=1000")(stdout=DIFF_STDOUT)
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

    result = main.action(
        config=pull_request_config(
            GITHUB_OUTPUT=output_file,
            GITHUB_STEP_SUMMARY=summary_file,
            GITHUB_BASE_REF="foo",
        ),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    # Check that no annotations were made
    output = capsys.readouterr()
    assert output.err.strip() == ""

    comment_file = pathlib.Path("python-coverage-comment-action.txt").read_text()
    assert comment == comment_file
    assert comment == summary_file.read_text()
    assert (
        "Previous coverage rate is not available, cannot report on evolution."
        in comment
    )


def test_action__pull_request__post_comment(
    pull_request_config, session, in_integration_env, output_file, summary_file, git
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )

    payload = json.dumps({"coverage": 30.00})
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(text=payload, headers={"content-type": "application/vnd.github.raw+json"})

    # Who am I
    session.register("GET", "/user")(json={"login": "foo"})
    # Are there already comments
    session.register("GET", "/repos/py-cov-action/foobar/issues/2/comments")(json=[])

    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

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
        "/repos/py-cov-action/foobar/issues/2/comments",
        json=checker,
    )(
        status_code=200,
    )

    result = main.action(
        config=pull_request_config(
            GITHUB_OUTPUT=output_file, GITHUB_STEP_SUMMARY=summary_file
        ),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    assert not pathlib.Path("python-coverage-comment-action.txt").exists()
    assert "Coverage for the whole project went from 30% to 77.77%" in comment
    assert comment.count("<img") == 10
    assert comment == summary_file.read_text()

    expected_output = "COMMENT_FILE_WRITTEN=false\n"

    assert output_file.read_text() == expected_output


def test_action__push__non_default_branch(
    push_config, session, in_integration_env, output_file, summary_file, git
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    git.register("git fetch origin main --depth=1000")(stdout=DIFF_STDOUT)
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

    payload = json.dumps({"coverage": 30.00})
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(text=payload, headers={"content-type": "application/vnd.github.raw+json"})

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/pulls",
        params={
            "state": "open",
            "head": "py-cov-action:other",
            "sort": "updated",
            "direction": "desc",
        },
    )(json=[{"number": 2}])

    # Who am I
    session.register("GET", "/user")(json={"login": "foo"})
    # Are there already comments
    session.register("GET", "/repos/py-cov-action/foobar/issues/2/comments")(json=[])

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
        "/repos/py-cov-action/foobar/issues/2/comments",
        json=checker,
    )(
        status_code=200,
    )
    result = main.action(
        config=push_config(
            GITHUB_REF="refs/heads/other",
            GITHUB_STEP_SUMMARY=summary_file,
            GITHUB_OUTPUT=output_file,
        ),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    assert not pathlib.Path("python-coverage-comment-action.txt").exists()
    assert "Coverage for the whole project went from 30% to 77.77%" in comment
    assert comment == summary_file.read_text()

    expected_output = "COMMENT_FILE_WRITTEN=false\n"

    assert output_file.read_text() == expected_output


def test_action__push__no_branch(
    push_config, session, in_integration_env, git, get_logs
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )

    result = main.action(
        config=push_config(
            GITHUB_REF="refs/tags/v1.0.0",
        ),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0
    assert get_logs("INFO", "This worflow is not triggered on a pull_request event")


def test_action__push__non_default_branch__no_pr(
    push_config, session, in_integration_env, output_file, summary_file, git
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    git.register("git fetch origin main --depth=1000")(stdout=DIFF_STDOUT)
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

    payload = json.dumps({"coverage": 30.00})
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(text=payload, headers={"content-type": "application/vnd.github.raw+json"})

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/pulls",
        params={
            "state": "open",
            "head": "py-cov-action:other",
            "sort": "updated",
            "direction": "desc",
        },
    )(json=[])
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/pulls",
        params={
            "state": "all",
            "head": "py-cov-action:other",
            "sort": "updated",
            "direction": "desc",
        },
    )(json=[])

    result = main.action(
        config=push_config(
            GITHUB_REF="refs/heads/other",
            GITHUB_STEP_SUMMARY=summary_file,
            GITHUB_OUTPUT=output_file,
        ),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    assert pathlib.Path("python-coverage-comment-action.txt").exists()

    expected_output = "COMMENT_FILE_WRITTEN=true\n"

    assert output_file.read_text() == expected_output


def test_action__pull_request__force_store_comment(
    pull_request_config, session, in_integration_env, output_file, git
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )

    payload = json.dumps({"coverage": 30.00})
    # There is an existing badge in this test, allowing to test the coverage evolution
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(text=payload, headers={"content-type": "application/vnd.github.raw+json"})

    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

    result = main.action(
        config=pull_request_config(FORCE_WORKFLOW_RUN=True, GITHUB_OUTPUT=output_file),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    assert pathlib.Path("python-coverage-comment-action.txt").exists()

    expected_output = "COMMENT_FILE_WRITTEN=true\n"

    assert output_file.read_text() == expected_output


def test_action__pull_request__post_comment__no_marker(
    pull_request_config, session, in_integration_env, get_logs, git
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )

    # No existing badge in this test
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(status_code=404)

    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

    result = main.action(
        config=pull_request_config(COMMENT_TEMPLATE="""foo"""),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 1
    assert get_logs("ERROR", "Marker not found")


def test_action__pull_request__annotations(
    pull_request_config, session, in_integration_env, capsys, git
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    # No existing badge in this test
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(status_code=404)

    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

    # Who am I
    session.register("GET", "/user")(json={"login": "foo"})
    # Are there already comments
    session.register("GET", "/repos/py-cov-action/foobar/issues/2/comments")(json=[])

    # Post a new comment
    session.register(
        "POST",
        "/repos/py-cov-action/foobar/issues/2/comments",
    )(status_code=200)

    result = main.action(
        config=pull_request_config(ANNOTATE_MISSING_LINES=True),
        github_session=session,
        http_session=session,
        git=git,
    )
    expected = """::group::Annotations of lines with missing coverage
::warning file=foo.py,line=12,endLine=12,title=Missing coverage::Missing coverage on line 12
::endgroup::"""
    output = capsys.readouterr()

    assert result == 0
    assert output.err.strip() == expected


def test_action__pull_request__post_comment__template_error(
    pull_request_config, session, in_integration_env, get_logs, git
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )

    # No existing badge in this test
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/contents/data.json",
    )(status_code=404)

    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=DIFF_STDOUT)

    result = main.action(
        config=pull_request_config(COMMENT_TEMPLATE="""{%"""),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 1
    assert get_logs("ERROR", "There was a rendering error")


def test_action__push__default_branch(
    push_config, session, in_integration_env, get_logs, git, summary_file
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    session.register(
        "GET",
        "https://img.shields.io/static/v1?label=Coverage&message=77%25&color=orange",
    )(text="<this is a svg badge>")

    git.register("git branch --show-current")(stdout="foo")
    git.register("git reset --hard")()
    git.register("git fetch origin python-coverage-comment-action-data")()
    git.register("git switch python-coverage-comment-action-data")()
    git.register("git add endpoint.json")()
    git.register("git add data.json")()
    git.register("git add badge.svg")()
    git.register("git add htmlcov")()
    git.register("git add README.md")()
    git.register("git diff --staged --exit-code")(exit_code=1)
    git.register("git commit --message Update coverage data")()
    git.register("git push origin python-coverage-comment-action-data")()
    git.register("git switch foo")()

    result = main.action(
        config=push_config(GITHUB_STEP_SUMMARY=summary_file),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    assert not get_logs("INFO", "Skipping badge")
    assert get_logs("INFO", "Saving coverage files")

    log = get_logs("INFO", "Badge SVG available at")[0]
    expected = """You can browse the full coverage report at:
    https://htmlpreview.github.io/?https://github.com/py-cov-action/foobar/blob/python-coverage-comment-action-data/htmlcov/index.html

You can use the following URLs to display your badge:

- Badge SVG available at:
    https://raw.githubusercontent.com/py-cov-action/foobar/python-coverage-comment-action-data/badge.svg

- Badge from shields endpoint is easier to customize but doesn't work with private repo:
    https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/py-cov-action/foobar/python-coverage-comment-action-data/endpoint.json

- Badge from shields dynamic url (less useful but you never know):
    https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fpy-cov-action%2Ffoobar%2Fpython-coverage-comment-action-data%2Fendpoint.json

See more details and ready-to-copy-paste-markdown at:
    https://github.com/py-cov-action/foobar/tree/python-coverage-comment-action-data"""
    assert log == expected

    summary_content = summary_file.read_text()

    assert "## Coverage report" in summary_content
    assert "Name" in summary_content
    assert "Stmts" in summary_content
    assert "Missing" in summary_content


def test_action__push__default_branch__private(
    push_config, session, in_integration_env, get_logs, git
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "private"}
    )
    session.register(
        "GET",
        "https://img.shields.io/static/v1?label=Coverage&message=77%25&color=orange",
    )(text="<this is a svg badge>")

    git.register("git branch --show-current")(stdout="foo")
    git.register("git reset --hard")()
    git.register("git fetch origin python-coverage-comment-action-data")()
    git.register("git switch python-coverage-comment-action-data")()
    git.register("git add endpoint.json")()
    git.register("git add data.json")()
    git.register("git add badge.svg")()
    git.register("git add README.md")()
    git.register("git diff --staged --exit-code")(exit_code=1)
    git.register("git commit --message Update coverage data")()
    git.register("git push origin python-coverage-comment-action-data")()
    git.register("git switch foo")()

    result = main.action(
        config=push_config(),
        github_session=session,
        http_session=session,
        git=git,
    )
    assert result == 0

    assert not get_logs("INFO", "Skipping badge")
    assert get_logs("INFO", "Saving coverage files")

    log = get_logs("INFO", "Badge SVG available at")[0]
    expected = """You can use the following URLs to display your badge:

- Badge SVG available at:
    https://github.com/py-cov-action/foobar/raw/python-coverage-comment-action-data/badge.svg

See more details and ready-to-copy-paste-markdown at:
    https://github.com/py-cov-action/foobar/tree/python-coverage-comment-action-data"""
    assert log == expected


def test_action__workflow_run__no_pr_number(
    workflow_run_config, session, in_integration_env, get_logs
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )

    result = main.action(
        config=workflow_run_config(GITHUB_PR_RUN_ID=None),
        github_session=session,
        http_session=session,
        git=None,
    )

    assert result == 1
    assert get_logs("ERROR", "Missing input GITHUB_PR_RUN_ID")


def test_action__workflow_run__no_pr(
    workflow_run_config, session, in_integration_env, get_logs
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    session.register("GET", "/user")(json={"login": "foo"})
    session.register("GET", "/repos/py-cov-action/foobar/actions/runs/123")(
        json={
            "head_branch": "branch",
            "head_repository": {"owner": {"login": "bar/repo-name"}},
        }
    )

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/pulls",
        params={
            "head": "bar/repo-name:branch",
            "sort": "updated",
            "direction": "desc",
            "state": "open",
        },
    )(json=[])
    session.register(
        "GET",
        "/repos/py-cov-action/foobar/pulls",
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
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    session.register("GET", "/user")(json={"login": "foo"})
    session.register("GET", "/repos/py-cov-action/foobar/actions/runs/123")(
        json={
            "head_branch": "branch",
            "head_repository": {"owner": {"login": "bar/repo-name"}},
        }
    )

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/pulls",
        params={
            "head": "bar/repo-name:branch",
            "sort": "updated",
            "direction": "desc",
            "state": "open",
        },
    )(json=[{"number": 456}])

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/actions/runs/123/artifacts",
    )(json={"artifacts": [{"name": "wrong_name"}], "total_count": 1})

    result = main.action(
        config=workflow_run_config(),
        github_session=session,
        http_session=session,
        git=None,
    )

    assert result == 0
    assert get_logs("INFO", "Artifact was not found")


def test_action__workflow_run__post_comment(
    workflow_run_config, session, in_integration_env, get_logs, zip_bytes, summary_file
):
    session.register("GET", "/repos/py-cov-action/foobar")(
        json={"default_branch": "main", "visibility": "public"}
    )
    session.register("GET", "/user")(json={"login": "foo"})
    session.register("GET", "/repos/py-cov-action/foobar/actions/runs/123")(
        json={
            "head_branch": "branch",
            "head_repository": {"owner": {"login": "bar/repo-name"}},
        }
    )

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/pulls",
        params={
            "head": "bar/repo-name:branch",
            "sort": "updated",
            "direction": "desc",
            "state": "open",
        },
    )(json=[{"number": 456}])

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/actions/runs/123/artifacts",
    )(
        json={
            "artifacts": [{"name": "python-coverage-comment-action", "id": 789}],
            "total_count": 1,
        }
    )

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/actions/artifacts/789/zip",
    )(content=zip_bytes(filename="python-coverage-comment-action.txt", content="Hey!"))

    session.register(
        "GET",
        "/repos/py-cov-action/foobar/issues/456/comments",
    )(json=[])

    session.register(
        "POST",
        "/repos/py-cov-action/foobar/issues/456/comments",
        json={"body": "Hey!"},
    )()

    result = main.action(
        config=workflow_run_config(GITHUB_STEP_SUMMARY=summary_file),
        github_session=session,
        http_session=session,
        git=None,
    )

    assert result == 0
    assert get_logs("INFO", "Comment file found in artifact, posting to PR")
    assert get_logs("INFO", "Comment posted in PR")
    assert summary_file.read_text() == ""
