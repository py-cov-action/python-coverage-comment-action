import subprocess


class SubProcessError(Exception):
    pass


def run(*args, **kwargs):
    # Ugly temporary debug step
    import pathlib

    print(pathlib.Path("codebase/code.py").read_text())
    import time

    time.sleep(5)
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
