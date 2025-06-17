from __future__ import annotations

import pathlib

import pytest

from coverage_comment import github


@pytest.mark.parametrize(
    "ref, expected",
    [
        ("refs/heads/main", True),
        ("refs/heads/other", False),
    ],
)
def test_is_default_branch(ref, expected):
    info = github.RepositoryInfo(default_branch="main", visibility="public")
    result = info.is_default_branch(ref=ref)

    assert result is expected


@pytest.mark.parametrize(
    "visibility, expected",
    [
        ("private", False),
        ("internal", False),
        ("public", True),
    ],
)
def test_is_public(visibility, expected):
    info = github.RepositoryInfo(default_branch="main", visibility=visibility)
    result = info.is_public()

    assert result is expected


def test_get_repository_info(gh, session):
    session.register("GET", "/repos/foo/bar")(
        json={"default_branch": "baz", "visibility": "public"}
    )

    info = github.get_repository_info(github=gh, repository="foo/bar")

    assert info == github.RepositoryInfo(default_branch="baz", visibility="public")


@pytest.mark.parametrize(
    "api_url, expected",
    [
        ("https://api.github.com/repos/foo/bar", "https://github.com"),
        ("https://api.github.com:8080/repos/foo/bar", "https://github.com:8080"),
        ("https://api.github.com/repos/foo/bar/issues", "https://github.com"),
        (
            "https://my-ghe.company.com/api/v3/repos/foo/bar",
            "https://my-ghe.company.com",
        ),
        (
            "https://my-ghe.company.com/api/v3/repos/foo/bar/issues",
            "https://my-ghe.company.com",
        ),
    ],
)
def test_extract_github_host(api_url, expected):
    result = github.extract_github_host(api_url=api_url)
    assert result == expected


def test_download_artifact(gh, session, zip_bytes):
    artifacts = [
        {"name": "bar", "id": 456},
        {"name": "foo", "id": 789},
    ]
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts, "total_count": 2}
    )

    session.register("GET", "/repos/foo/bar/actions/artifacts/789/zip")(
        content=zip_bytes(filename="foo.txt", content="bar")
    )

    result = github.download_artifact(
        github=gh,
        repository="foo/bar",
        artifact_name="foo",
        run_id=123,
        filename=pathlib.Path("foo.txt"),
    )

    assert result == "bar"


def test_download_artifact_from_page_2(gh, session, zip_bytes):
    artifacts_page_1 = [
        {"name": "test", "id": 000},
    ]
    artifacts_page_2 = [
        {"name": "bar", "id": 456},
        {"name": "foo", "id": 789},
    ]
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts_page_1, "total_count": 3}
    )
    session.register(
        "GET",
        "/repos/foo/bar/actions/runs/123/artifacts",
        params={"page": "2"},
    )(json={"artifacts": artifacts_page_2, "total_count": 3})

    session.register("GET", "/repos/foo/bar/actions/artifacts/789/zip")(
        content=zip_bytes(filename="foo.txt", content="bar")
    )

    result = github.download_artifact(
        github=gh,
        repository="foo/bar",
        artifact_name="foo",
        run_id=123,
        filename=pathlib.Path("foo.txt"),
    )

    assert result == "bar"


def test_download_artifact__no_artifact(gh, session):
    artifacts = [
        {"name": "bar", "id": 456},
    ]
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts, "total_count": 1}
    )

    with pytest.raises(github.NoArtifact):
        github.download_artifact(
            github=gh,
            repository="foo/bar",
            artifact_name="foo",
            run_id=123,
            filename=pathlib.Path("foo.txt"),
        )


def test_download_artifact__no_file(gh, session, zip_bytes):
    artifacts = [{"name": "foo", "id": 789}]
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts}
    )
    session.register(
        "GET",
        "/repos/foo/bar/actions/runs/123/artifacts",
        params={"page": "2"},
    )(json={})

    session.register("GET", "/repos/foo/bar/actions/artifacts/789/zip")(
        content=zip_bytes(filename="foo.txt", content="bar")
    )
    with pytest.raises(github.NoArtifact):
        github.download_artifact(
            github=gh,
            repository="foo/bar",
            artifact_name="foo",
            run_id=123,
            filename=pathlib.Path("bar.txt"),
        )


def test_fetch_artifacts_empty_response(gh, session):
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": [], "total_count": 0}
    )

    repo_path = gh.repos("foo/bar")

    result = github._fetch_artifacts(
        repo_path=repo_path,
        run_id=123,
    )

    assert not list(result)


def test_fetch_artifacts_single_page(gh, session):
    artifacts = [{"name": "bar", "id": 456}]

    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts, "total_count": 1}
    )

    repo_path = gh.repos("foo/bar")

    result = github._fetch_artifacts(
        repo_path=repo_path,
        run_id=123,
    )

    assert list(result) == artifacts


def test_fetch_artifacts_multiple_pages(gh, session):
    artifacts_page_1 = [{"name": "bar", "id": 456}]
    artifacts_page_2 = [{"name": "bar", "id": 789}]

    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts_page_1, "total_count": 2}
    )
    session.register(
        "GET", "/repos/foo/bar/actions/runs/123/artifacts", params={"page": "2"}
    )(json={"artifacts": artifacts_page_2, "total_count": 2})

    repo_path = gh.repos("foo/bar")

    result = github._fetch_artifacts(
        repo_path=repo_path,
        run_id=123,
    )

    assert list(result) == artifacts_page_1 + artifacts_page_2


def test_get_branch_from_workflow_run(gh, session):
    json = {
        "head_branch": "other",
        "head_repository": {"owner": {"login": "someone"}},
    }
    session.register("GET", "/repos/foo/bar/actions/runs/123")(json=json)

    owner, branch = github.get_branch_from_workflow_run(
        github=gh, repository="foo/bar", run_id=123
    )

    assert owner == "someone"
    assert branch == "other"


def test_find_pr_for_branch(gh, session):
    params = {
        "head": "someone:other",
        "sort": "updated",
        "direction": "desc",
        "state": "open",
    }
    session.register("GET", "/repos/foo/bar/pulls", params=params)(
        json=[{"number": 456}]
    )

    result = github.find_pr_for_branch(
        github=gh, repository="foo/bar", owner="someone", branch="other"
    )

    assert result == 456


def test_find_pr_for_branch__no_open_pr(gh, session):
    params = {
        "head": "someone:other",
        "sort": "updated",
        "direction": "desc",
    }
    session.register(
        "GET",
        "/repos/foo/bar/pulls",
        params=params | {"state": "open"},
    )(json=[])
    session.register(
        "GET",
        "/repos/foo/bar/pulls",
        params=params | {"state": "all"},
    )(json=[{"number": 456}])

    result = github.find_pr_for_branch(
        github=gh, repository="foo/bar", owner="someone", branch="other"
    )

    assert result == 456


def test_find_pr_for_branch__no_pr(gh, session):
    params = {
        "head": "someone:other",
        "sort": "updated",
        "direction": "desc",
    }
    session.register(
        "GET",
        "/repos/foo/bar/pulls",
        params=params | {"state": "open"},
    )(json=[])
    session.register(
        "GET",
        "/repos/foo/bar/pulls",
        params=params | {"state": "all"},
    )(json=[])
    with pytest.raises(github.CannotDeterminePR):
        github.find_pr_for_branch(
            github=gh, repository="foo/bar", owner="someone", branch="other"
        )


def test_get_my_login(gh, session):
    session.register("GET", "/user")(json={"login": "foo"})

    result = github.get_my_login(github=gh)

    assert result == "foo"


def test_get_my_login__github_bot(gh, session):
    session.register("GET", "/user")(status_code=403)

    result = github.get_my_login(github=gh)

    assert result == "github-actions[bot]"


@pytest.mark.parametrize(
    "existing_comments",
    [
        # No pre-existing comment
        [],
        # Comment by correct author without marker
        [{"user": {"login": "foo"}, "body": "Hey! hi! how are you?", "id": 456}],
        # Comment by other author with marker
        [{"user": {"login": "bar"}, "body": "Hey marker!", "id": 456}],
    ],
)
def test_post_comment__create(gh, session, get_logs, existing_comments):
    session.register("GET", "/repos/foo/bar/issues/123/comments")(
        json=existing_comments
    )
    session.register(
        "POST", "/repos/foo/bar/issues/123/comments", json={"body": "hi!"}
    )()

    github.post_comment(
        github=gh,
        me="foo",
        repository="foo/bar",
        pr_number=123,
        contents="hi!",
        marker="marker",
    )

    assert get_logs("INFO", "Adding new comment")


def test_post_comment__create_error(gh, session):
    session.register("GET", "/repos/foo/bar/issues/123/comments")(json=[])
    session.register(
        "POST", "/repos/foo/bar/issues/123/comments", json={"body": "hi!"}
    )(status_code=403)

    with pytest.raises(github.CannotPostComment):
        github.post_comment(
            github=gh,
            me="foo",
            repository="foo/bar",
            pr_number=123,
            contents="hi!",
            marker="marker",
        )


def test_post_comment__update(gh, session, get_logs):
    comment = {
        "user": {"login": "foo"},
        "body": "Hey! Hi! How are you? marker",
        "id": 456,
    }
    session.register("GET", "/repos/foo/bar/issues/123/comments")(json=[comment])
    session.register(
        "PATCH", "/repos/foo/bar/issues/comments/456", json={"body": "hi!"}
    )()

    github.post_comment(
        github=gh,
        me="foo",
        repository="foo/bar",
        pr_number=123,
        contents="hi!",
        marker="marker",
    )

    assert get_logs("INFO", "Update previous comment")


def test_post_comment__update_error(gh, session):
    comment = {
        "user": {"login": "foo"},
        "body": "Hey! Hi! How are you? marker",
        "id": 456,
    }
    session.register("GET", "/repos/foo/bar/issues/123/comments")(json=[comment])
    session.register(
        "PATCH", "/repos/foo/bar/issues/comments/456", json={"body": "hi!"}
    )(status_code=403)

    with pytest.raises(github.CannotPostComment):
        github.post_comment(
            github=gh,
            me="foo",
            repository="foo/bar",
            pr_number=123,
            contents="hi!",
            marker="marker",
        )


def test_set_output(output_file):
    github.set_output(github_output=output_file, foo=True)

    assert output_file.read_text() == "foo=true\n"


def test_set_output__empty():
    assert github.set_output(github_output=None, foo=True) is None


def test_get_workflow_command():
    output = github.get_workflow_command(
        command="foo", command_value="bar", file="main.py", line="1", title="someTitle"
    )

    assert output == "::foo file=main.py,line=1,title=someTitle::bar"


def test_get_workflow_command_no_kwargs():
    output = github.get_workflow_command(command="group", command_value="title")

    assert output == "::group::title"


def test_send_workflow_command(capsys):
    github.send_workflow_command(
        command="foo", command_value="bar", file="main.py", line="1", title="someTitle"
    )
    output = capsys.readouterr()
    assert output.err.strip() == "::foo file=main.py,line=1,title=someTitle::bar"


def test_add_job_summary(summary_file):
    github.add_job_summary(
        content="[job summary part 1]\n", github_step_summary=summary_file
    )
    assert summary_file.read_text() == "[job summary part 1]\n"

    github.add_job_summary(
        content="[job summary part 2]", github_step_summary=summary_file
    )
    assert summary_file.read_text() == "[job summary part 1]\n[job summary part 2]"


def test_annotations(capsys):
    github.create_missing_coverage_annotations(
        annotation_type="warning",
        annotations=[
            (pathlib.Path("codebase/code.py"), 1, 3),
            (pathlib.Path("codebase/other.py"), 5, 5),
        ],
    )

    expected = """::group::Annotations of lines with missing coverage
::warning file=codebase/code.py,line=1,endLine=3,title=Missing coverage::Missing coverage on lines 1-3
::warning file=codebase/other.py,line=5,endLine=5,title=Missing coverage::Missing coverage on line 5
::endgroup::"""
    output = capsys.readouterr()
    assert output.err.strip() == expected
