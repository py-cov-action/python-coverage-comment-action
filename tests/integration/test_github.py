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


def test_download_artifact(gh, session, zip_bytes):

    artifacts = [
        {"name": "bar", "id": 456},
        {"name": "foo", "id": 789},
    ]
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts}
    )

    session.register("GET", "/repos/foo/bar/actions/artifacts/789/zip")(
        content=zip_bytes(filename="foo.txt", content="bar")
    )

    result = github.download_artifact(
        github=gh,
        repository="foo/bar",
        artifact_name="foo",
        run_id="123",
        filename="foo.txt",
    )

    assert result == "bar"


def test_download_artifact__no_artifact(gh, session):

    artifacts = [
        {"name": "bar", "id": 456},
    ]
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts}
    )

    with pytest.raises(github.NoArtifact):
        github.download_artifact(
            github=gh,
            repository="foo/bar",
            artifact_name="foo",
            run_id="123",
            filename="foo.txt",
        )


def test_download_artifact__no_file(gh, session, zip_bytes):

    artifacts = [
        {"name": "foo", "id": 789},
    ]
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts}
    )

    session.register("GET", "/repos/foo/bar/actions/artifacts/789/zip")(
        content=zip_bytes(filename="foo.txt", content="bar")
    )
    with pytest.raises(github.NoArtifact):
        github.download_artifact(
            github=gh,
            repository="foo/bar",
            artifact_name="foo",
            run_id="123",
            filename="bar.txt",
        )


def test_get_pr_number_from_workflow_run(gh, session):
    json = {
        "head_branch": "other",
        "head_repository": {"full_name": "someone/repo-name"},
    }
    session.register("GET", "/repos/foo/bar/actions/runs/123")(json=json)
    params = {
        "head": "someone/repo-name:other",
        "sort": "updated",
        "direction": "desc",
        "state": "open",
    }
    session.register("GET", "/repos/foo/bar/pulls", params=params)(
        json=[{"number": 456}]
    )

    result = github.get_pr_number_from_workflow_run(
        github=gh, repository="foo/bar", run_id=123
    )

    assert result == 456


def test_get_pr_number_from_workflow_run__no_open_pr(gh, session):
    json = {
        "head_branch": "other",
        "head_repository": {"full_name": "someone/repo-name"},
    }
    session.register("GET", "/repos/foo/bar/actions/runs/123")(json=json)
    params = {
        "head": "someone/repo-name:other",
        "sort": "updated",
        "direction": "desc",
    }
    session.register("GET", "/repos/foo/bar/pulls", params=params | {"state": "open"})(
        json=[]
    )
    session.register("GET", "/repos/foo/bar/pulls", params=params | {"state": "all"})(
        json=[{"number": 456}]
    )

    result = github.get_pr_number_from_workflow_run(
        github=gh, repository="foo/bar", run_id=123
    )

    assert result == 456


def test_get_pr_number_from_workflow_run__no_pr(gh, session):
    json = {
        "head_branch": "other",
        "head_repository": {"full_name": "someone/repo-name"},
    }
    session.register("GET", "/repos/foo/bar/actions/runs/123")(json=json)
    params = {
        "head": "someone/repo-name:other",
        "sort": "updated",
        "direction": "desc",
    }
    session.register("GET", "/repos/foo/bar/pulls", params=params | {"state": "open"})(
        json=[]
    )
    session.register("GET", "/repos/foo/bar/pulls", params=params | {"state": "all"})(
        json=[]
    )
    with pytest.raises(github.CannotDeterminePR):
        github.get_pr_number_from_workflow_run(
            github=gh, repository="foo/bar", run_id=123
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


def test_set_output(capsys):
    github.set_output(foo=True)
    captured = capsys.readouterr()
    assert captured.out.strip() == "::set-output name=foo::true"
