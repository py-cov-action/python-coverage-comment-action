import io
import zipfile

import httpx
import pytest

from coverage_comment import github, github_client


def test_get_api():
    assert isinstance(github.get_api(token="foo"), github_client.GitHub)


@pytest.fixture
def session():
    """
    You get a session object. Register responses on it:
    session.register(method="GET", path="/a/b")(status_code=200)

    if session.request(method="GET", path="/a/b") is called, it will return a response
    with status_code 200. Also if not called by the end of the test, it will raise.
    """

    class Session:
        responses = []  # List[Tuples[request kwargs, response kwargs]]

        def request(self, method, path, **kwargs):
            kwargs = {"method": method, "path": path} | kwargs

            for i, (request_kwargs, response_kwargs) in enumerate(self.responses):
                if all(
                    kwargs.get(key, object()) == value
                    for key, value in request_kwargs.items()
                ):
                    self.responses.pop(i)
                    return httpx.Response(
                        **response_kwargs,
                        request=httpx.Request(method=method, url=path),
                    )
            assert (
                False
            ), f"No response found for kwargs {kwargs}\nExpected answers are {self.responses}"

        def register(self, method, path, **request_kwargs):
            request_kwargs = {"method": method, "path": path} | request_kwargs

            def _(**response_kwargs):
                response_kwargs.setdefault("status_code", 200)
                self.responses.append((request_kwargs, response_kwargs))

            return _

    session = Session()
    yield session
    assert not session.responses


@pytest.fixture
def gh(session):
    return github_client.GitHub(access_token="foo", session=session)


@pytest.mark.parametrize(
    "branch, expected",
    [
        ("refs/heads/main", True),
        ("refs/heads/other", False),
    ],
)
def test_is_default_branch(gh, session, branch, expected):
    session.register("GET", "/repos/foo/bar")(json={"default_branch": "main"})

    result = github.is_default_branch(github=gh, repository="foo/bar", branch=branch)

    assert result is expected


@pytest.fixture
def zip_bytes():
    file = io.BytesIO()
    with zipfile.ZipFile(file, mode="w") as zipf:
        with zipf.open("foo.txt", "w") as subfile:
            subfile.write(b"bar")
    zip_bytes = file.getvalue()
    assert zip_bytes.startswith(b"PK")
    return zip_bytes


def test_download_artifact(gh, session, zip_bytes):

    artifacts = [
        {"name": "bar", "id": 456},
        {"name": "foo", "id": 789},
    ]
    session.register("GET", "/repos/foo/bar/actions/runs/123/artifacts")(
        json={"artifacts": artifacts}
    )

    session.register("GET", "/repos/foo/bar/actions/artifacts/789/zip")(
        content=zip_bytes
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
        content=zip_bytes
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
    json = {"head_branch": "other", "head_repository": {"owner": {"login": "someone"}}}
    session.register("GET", "/repos/foo/bar/actions/runs/123")(json=json)
    params = {
        "head": "someone:other",
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
    json = {"head_branch": "other", "head_repository": {"owner": {"login": "someone"}}}
    session.register("GET", "/repos/foo/bar/actions/runs/123")(json=json)
    params = {
        "head": "someone:other",
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
    json = {"head_branch": "other", "head_repository": {"owner": {"login": "someone"}}}
    session.register("GET", "/repos/foo/bar/actions/runs/123")(json=json)
    params = {
        "head": "someone:other",
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
def test_post_comment__create(gh, session, caplog, existing_comments):
    caplog.set_level("INFO")
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

    assert "Adding new comment" in caplog.messages


def test_post_comment__create_error(gh, session, caplog):
    caplog.set_level("INFO")
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


def test_post_comment__update(gh, session, caplog):
    caplog.set_level("INFO")
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

    assert "Update previous comment" in caplog.messages


def test_set_output(capsys):
    github.set_output(foo=True)
    captured = capsys.readouterr()
    assert captured.out.strip() == "::set-output name=foo::true"
