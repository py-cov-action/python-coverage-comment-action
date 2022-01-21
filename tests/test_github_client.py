import httpx
import pytest

from coverage_comment import github_client


def test_github_client__get(mocker):
    Client = mocker.patch("httpx.Client")

    gh = github_client.GitHub(access_token="foo")
    response = Client.return_value.request.return_value
    response.headers = {"content-type": "application/json"}
    response.json.return_value = {"foo": "bar"}

    assert gh.repos("a/b").issues().get(a=1) == {"foo": "bar"}

    assert Client.mock_calls == [
        mocker.call(
            base_url="https://api.github.com",
            follow_redirects=True,
            headers={"Authorization": "token foo"},
        ),
        mocker.call().request(
            "GET",
            "/repos/a/b/issues",
            timeout=60,
            params={"a": 1},
        ),
        mocker.call().request().json(object_hook=github_client.JsonObject),
        mocker.call().request().raise_for_status(),
    ]


def test_github_client__post_non_json(mocker):
    Client = mocker.patch("httpx.Client")
    Client.return_value.request.return_value.headers = {}
    gh = github_client.GitHub(access_token="foo")

    gh.repos("a/b").issues().post(a=1)

    assert Client.mock_calls == [
        mocker.call(
            base_url="https://api.github.com",
            follow_redirects=True,
            headers={"Authorization": "token foo"},
        ),
        mocker.call().request(
            "POST",
            "/repos/a/b/issues",
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


def test_github_client__get_error(mocker):
    Client = mocker.patch("httpx.Client")

    gh = github_client.GitHub(access_token="foo")
    response = Client.return_value.request.return_value
    response.headers = {"content-type": "application/json"}
    response.json.return_value = {"foo": "bar"}
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "", request=None, response=response
    )

    with pytest.raises(github_client.ApiError) as exc_info:
        gh.repos.get()

    assert str(exc_info.value) == "{'foo': 'bar'}"


def test_github_client__get_error_non_json(mocker):
    Client = mocker.patch("httpx.Client")

    gh = github_client.GitHub(access_token="foo")
    response = Client.return_value.request.return_value
    response.headers = {"content-type": "text/plain"}
    response.text = "{foobar"
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "", request=None, response=response
    )

    with pytest.raises(github_client.ApiError) as exc_info:
        gh.repos.get()

    assert str(exc_info.value) == "{foobar"
