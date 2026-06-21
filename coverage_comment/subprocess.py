from __future__ import annotations

import base64
import functools
import os
import pathlib
import subprocess
from typing import Any, Self

from coverage_comment import log


class SubProcessError(Exception):
    def __init__(
        self,
        args: list[str],
        returncode: int,
        stderr: str,
        stdout: str,
        exc: subprocess.CalledProcessError,
    ):
        self.exc_args: list[str] = args
        self.returncode: int = returncode
        self.stderr: str = stderr
        self.stdout: str = stdout
        self.exc: subprocess.CalledProcessError = exc
        message = f"Error on command: {args=} {returncode=}\n{stderr=}\n{stdout=}"
        super().__init__(message)

    @classmethod
    def from_called_process_error(cls, exc: subprocess.CalledProcessError) -> Self:
        return cls(
            args=exc.cmd,
            returncode=exc.returncode,
            stderr=exc.stderr,
            stdout=exc.stdout,
            exc=exc,
        )


class GitError(SubProcessError):
    pass


def run(*args: str, path: pathlib.Path, **kwargs: Any) -> str:
    try:
        call = subprocess.run(
            args,
            cwd=path,
            text=True,
            # Only relates to DecodeErrors while decoding the output
            errors="replace",
            check=True,
            capture_output=True,
            **kwargs,
        )
    except subprocess.CalledProcessError as exc:
        new_exc = SubProcessError.from_called_process_error(exc)
        new_exc.add_note(f"Launched from {path=} with {kwargs=}")
        raise new_exc from exc
    else:
        log.debug(
            f"Ran command: {args=} {path=} {kwargs=} {call.stderr=} {call.stdout=} {call.returncode=}"
        )
    return call.stdout


class Git:
    """
    Wrapper around calling git subprocesses in a way that reads a tiny bit like
    Python code.
    Call a method on git to call the corresponding subcommand (use `_` for `-`).
    Add string parameters for the rest of the command line.

    Returns stdout or raise GitError

    >>> git = Git()
    >>> git.clone(url)
    >>> git.commit("-m", message)
    >>> git.rev_parse("--short", "HEAD")
    """

    cwd: pathlib.Path = pathlib.Path(".")

    def __call__(
        self,
        *args: str,
        env: dict[str, str] | None = None,
        token: str | None = None,
        **kwargs: Any,
    ) -> str:
        # When setting the `env` argument to run, instead of inheriting env
        # vars from the current process, the whole environment of the
        # subprocess is whatever we pass. In other words, we can either
        # conditionally pass an `env` parameter, but it's less readable,
        # or we can always pass an `env` parameter, but in this case, we
        # need to always merge `os.environ` to it (and ensure our variables
        # have precedence)
        token_args = []
        token_env = {}
        if token is not None:
            token_args = ["--config-env=http.extraheader=GIT_EXTRA_HEADER"]
            encoded = base64.b64encode(f"x-access-token:{token}".encode()).decode()
            token_env = {"GIT_EXTRA_HEADER": f"Authorization: basic {encoded}"}
        try:
            return run(
                "git",
                *token_args,
                *args,
                path=self.cwd,
                env=os.environ | (env or {}) | token_env,
                **kwargs,
            )
        except SubProcessError as exc:
            raise GitError.from_called_process_error(exc.exc) from exc

    def __getattr__(self, name: str) -> Any:
        return functools.partial(self, name.replace("_", "-"))
