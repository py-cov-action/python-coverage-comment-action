#!/usr/bin/env python

"""
From: https://github.com/michaelliao/githubpy/blob/96d0c3e729c0b3e3c043a604547ccff17782ac2b/github.py
GitHub API Python SDK. (Python >= 2.6)
Apache License
Michael Liao (askxuefeng@gmail.com)
License: https://github.com/michaelliao/githubpy/blob/96d0c3e729c0b3e3c043a604547ccff17782ac2b/LICENSE.txt
"""

__version__ = "1.1.1"

import httpx

TIMEOUT = 60

_URL = "https://api.github.com"


class _Executable:
    def __init__(self, _gh, _method, _path):
        self._gh = _gh
        self._method = _method
        self._path = _path

    def __call__(self, **kw):
        return self._gh._http(self._method, self._path, **kw)


class _Callable:
    def __init__(self, _gh, _name):
        self._gh = _gh
        self._name = _name

    def __call__(self, *args):
        if len(args) == 0:
            return self
        name = "{}/{}".format(self._name, "/".join([str(arg) for arg in args]))
        return _Callable(self._gh, name)

    def __getattr__(self, attr):
        if attr in ["get", "put", "post", "patch", "delete"]:
            return _Executable(self._gh, attr, self._name)
        name = f"{self._name}/{attr}"
        return _Callable(self._gh, name)


class GitHub:

    """
    GitHub client.
    """

    def __init__(self, access_token):
        self.x_ratelimit_remaining = -1
        self.x_ratelimit_limit = -1
        self.x_ratelimit_reset = -1
        self._session = httpx.Client(
            follow_redirects=True,
            headers={"Authorization": f"token {access_token}"},
        )

    def __getattr__(self, attr):
        return _Callable(self, "/%s" % attr)

    def _http(self, _method, _path, **kw):
        _method = _method.lower()
        requests_kwargs = {}
        if _method == "get" and kw:
            requests_kwargs = {"params": kw}

        elif _method in ["post", "patch", "put"]:
            requests_kwargs = {"json": kw}

        try:
            response = self._session.request(
                _method.upper(),
                f"{_URL}{_path}",
                timeout=TIMEOUT,
                **requests_kwargs,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            is_json = self.is_json(exc.response.headers)

            cls: type[ApiError] = {
                403: Forbidden,
                404: NotFound,
            }.get(exc.response.status_code, ApiError)

            raise cls(response=exc.response) from exc

        is_json = self.is_json(response.headers)
        if is_json:
            return response.json(object_hook=JsonObject)
        else:
            return response.content

    def is_json(self, headers):
        return headers.get("content-type", "").startswith("application/json")


class JsonObject(dict):
    """
    general json object that can bind any fields but also act as a dict.
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)


class ApiError(Exception):
    def __init__(self, *args, response, **kwargs):
        super().__init__(args, kwargs)
        self.response = response


class NotFound(ApiError):
    pass


class Forbidden(ApiError):
    pass
