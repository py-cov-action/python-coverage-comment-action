import pytest

from coverage_comment import github_client


def test_github_client__get(mocker):
    Client = mocker.patch("httpx.Client")

    gh = github_client.GitHub(access_token="foo")
    Client.return_value.request.return_value.headers = {
        "content-type": "application/json"
    }

    gh.repos("a/b").issues().get(a=1)

    assert Client.mock_calls == [
        mocker.call(follow_redirects=True, headers={"Authorization": "token foo"}),
        mocker.call().request(
            "GET",
            "https://api.github.com/repos/a/b/issues",
            timeout=60,
            params={"a": 1},
        ),
        mocker.call().request().raise_for_status(),
        mocker.call().request().json(object_hook=github_client.JsonObject),
    ]


def test_github_client__post_non_json(mocker):
    Client = mocker.patch("httpx.Client")
    Client.return_value.request.return_value.headers = {}
    gh = github_client.GitHub(access_token="foo")

    gh.repos("a/b").issues().post(a=1)

    assert Client.mock_calls == [
        mocker.call(follow_redirects=True, headers={"Authorization": "token foo"}),
        mocker.call().request(
            "POST",
            "https://api.github.com/repos/a/b/issues",
            timeout=60,
            json={"a": 1},
        ),
        mocker.call().request().raise_for_status(),
    ]


def test_json_object():
    obj = github_client.JsonObject({"a": 1})

    assert obj.a == 1


def test_json_object__error():
    obj = github_client.JsonObject({"a": 1})

    with pytest.raises(AttributeError):
        obj.b
