import subprocess


class SubProcessError(Exception):
    pass


def run(*args, **kwargs):
    # Ugly temporary debug step
    print(subprocess.run(["pwd"], text=True, check=True, capture_output=True).stdout)
    print(
        subprocess.run(["ls", "-lR"], text=True, check=True, capture_output=True).stdout
    )
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
