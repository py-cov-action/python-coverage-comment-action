#!/usr/bin/env python

"""
From: https://github.com/michaelliao/githubpy/blob/96d0c3e729c0b3e3c043a604547ccff17782ac2b/github.py
GitHub API Python SDK. (Python >= 2.6)
Apache License
Michael Liao (askxuefeng@gmail.com)
License: https://github.com/michaelliao/githubpy/blob/96d0c3e729c0b3e3c043a604547ccff17782ac2b/LICENSE.txt
"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal, overload

__version__ = "1.1.1"

import httpx

TIMEOUT = 60

_URL = "https://api.github.com"

type Method = Literal["get", "post", "patch", "put", "delete"]


@dataclasses.dataclass
class HttpCall:
    gh: GitHub
    method: Method
    path: str

    @overload
    def __call__(
        self,
        *,
        text: Literal[False] = False,
        bytes: Literal[False] = False,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> JsonObject: ...

    @overload
    def __call__(
        self,
        *,
        text: Literal[True],
        bytes: Literal[False] = False,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> str: ...

    @overload
    def __call__(
        self,
        *,
        text: Literal[False] = False,
        bytes: Literal[True],
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> bytes: ...

    def __call__(
        self,
        text: bool = False,
        bytes: bool = False,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> JsonObject | str | bytes:
        return self.gh.http(
            self.method,
            self.path,
            text=text,
            bytes=bytes,
            headers=headers,
            **kwargs,
        )


@dataclasses.dataclass
class Endpoint:
    gh: GitHub
    name: str

    def __call__(self, *args: Any):
        if len(args) == 0:
            return self
        name = "{}/{}".format(self._name, "/".join([str(arg) for arg in args]))
        return Endpoint(self.gh, name)

    @property
    def get(self) -> HttpCall:
        return HttpCall(gh=self.gh, method="get", path=self.name)

    @property
    def post(self) -> HttpCall:
        return HttpCall(gh=self.gh, method="post", path=self.name)

    @property
    def put(self) -> HttpCall:
        return HttpCall(gh=self.gh, method="put", path=self.name)

    @property
    def patch(self) -> HttpCall:
        return HttpCall(gh=self.gh, method="patch", path=self.name)

    @property
    def delete(self) -> HttpCall:
        return HttpCall(gh=self.gh, method="delete", path=self.name)

    def __getattr__(self, attr: str) -> Endpoint:
        name = f"{self.name}/{attr}"
        return Endpoint(gh=self.gh, name=name)


@dataclasses.dataclass
class GitHub:
    """
    GitHub client.
    """

    session: httpx.Client

    def __getattr__(self, attr: str):
        return Endpoint(self, f"/{attr}")

    @overload
    def http(
        self,
        method: Method,
        path: str,
        *,
        text: Literal[False] = False,
        bytes: Literal[False] = False,
        headers: dict[str, str] | None,
        **kwargs: Any,
    ) -> JsonObject: ...

    @overload
    def http(
        self,
        method: Method,
        path: str,
        *,
        text: Literal[True],
        bytes: Literal[False] = False,
        headers: dict[str, str] | None,
        **kwargs: Any,
    ) -> str: ...

    @overload
    def http(
        self,
        method: Method,
        path: str,
        *,
        text: Literal[False] = False,
        bytes: Literal[True],
        headers: dict[str, str] | None,
        **kwargs: Any,
    ) -> bytes: ...

    @overload
    def http(
        self,
        method: Method,
        path: str,
        *,
        text: bool,
        bytes: bool,
        headers: dict[str, str] | None,
        **kwargs: Any,
    ) -> JsonObject | str | bytes: ...

    def http(
        self,
        method: Method,
        path: str,
        *,
        text: bool = False,
        bytes: bool = False,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> JsonObject | str | bytes:
        _method = method.lower()
        params: dict[str, Any] | None = None
        json: dict[str, Any] | None = None
        if _method == "get" and kwargs:
            params = kwargs

        elif _method in ["post", "patch", "put"]:
            json = kwargs

        response = self.session.request(
            _method.upper(),
            path,
            timeout=TIMEOUT,
            headers=headers,
            params=params,
            json=json,
        )
        contents: JsonObject | str | bytes = response_contents(
            response=response, text=text, bytes=bytes
        )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            cls: type[ApiError] = {
                403: Forbidden,
                404: NotFound,
            }.get(exc.response.status_code, ApiError)

            raise cls(str(contents)) from exc

        return contents


@overload
def response_contents(
    response: httpx.Response,
    *,
    text: Literal[False],
    bytes: Literal[True],
) -> bytes: ...


@overload
def response_contents(
    response: httpx.Response,
    *,
    text: Literal[True],
    bytes: Literal[False],
) -> str: ...


@overload
def response_contents(
    response: httpx.Response,
    *,
    text: Literal[False],
    bytes: Literal[False],
) -> JsonObject: ...


@overload
def response_contents(
    response: httpx.Response,
    *,
    text: bool,
    bytes: bool,
) -> JsonObject | str | bytes: ...


def response_contents(
    response: httpx.Response,
    *,
    text: bool,
    bytes: bool,
) -> JsonObject | str | bytes:
    if bytes:
        return response.content

    if text:
        return response.text

    if not response.headers.get("content-type", "").startswith("application/json"):
        raise InvalidResponseType(
            f"Response is requested as JSON but doesn't have proper content type. "
            f"Response: {response.text}"
        )

    return response.json(object_hook=JsonObject)


class JsonObject(dict[str, Any]):
    """
    general json object that can bind any fields but also act as a dict.
    """

    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(rf"'Dict' object has no attribute '{key}'")


class ApiError(Exception):
    pass


class NotFound(ApiError):
    pass


class Forbidden(ApiError):
    pass


class InvalidResponseType(ApiError):
    pass
