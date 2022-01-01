import subprocess


class SubProcessError(Exception):
    pass


def run(*args, **kwargs):
    try:
        return subprocess.run(
            args,
            text=True,
            check=True,
            capture_output=True,
            **kwargs,
        )
    except subprocess.CalledProcessError as exc:
        raise SubProcessError("/n".join([exc.stdout, exc.stderr])) from exc
