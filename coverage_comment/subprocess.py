import functools
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
    cwd = ""

    def _git(self, *args, **kwargs):
        try:
            return run(
                "git",
                *args,
                cwd=self.cwd,
                **kwargs,
            )
        except SubProcessError as exc:
            raise GitError from exc

    def __getattr__(self, name: str) -> Any:
        return functools.partial(self._git, name)
