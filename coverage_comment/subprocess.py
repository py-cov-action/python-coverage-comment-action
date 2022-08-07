import functools
import os
import subprocess
from typing import Any


class SubProcessError(Exception):
    pass


class GitError(SubProcessError):
    pass


def run(*args, **kwargs) -> str:
    try:
        return subprocess.run(
            args,
            text=True,
            check=True,
            capture_output=True,
            **kwargs,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise SubProcessError("/n".join([exc.stdout, exc.stderr])) from exc


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

    cwd = "."

    def _git(self, *args: str, env: dict[str, str] | None = None, **kwargs) -> str:
        # When setting the `env` argument to run, instead of inheriting env
        # vars from the current process, the whole environment of the
        # subprocess is whatever we pass. In other words, we can either
        # conditionnaly pass an `env` parameter, but it's less readable,
        # or we can always pass an `env` parameter, but in this case, we
        # need to always merge `os.environ` to it (and ensure our variables
        # have precedence)
        try:
            return run(
                "git",
                *args,
                cwd=self.cwd,
                env=os.environ | (env or {}),
                **kwargs,
            )
        except SubProcessError as exc:
            raise GitError from exc

    def __getattr__(self, name: str) -> Any:
        return functools.partial(self._git, name.replace("_", "-"))
