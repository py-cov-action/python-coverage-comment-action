import json as json_module
import os
import pathlib
import shutil
import subprocess
import time

import pytest

# In this directory, `gh` is not the global `gh` fixture, but is instead
# a fixture letting you use the `gh` CLI tool.


@pytest.fixture
def clean_gh_after_test():
    envvar = os.environ.get("COVERAGE_COMMENT_E2E_CLEAN_GITHUB_AFTER_TESTS", "")
    return envvar.lower() != "false"


@pytest.fixture
def call():
    def _(command, *args, env, **kwargs):
        try:
            call = subprocess.run(
                [command] + list(args),
                text=True,
                check=True,
                capture_output=True,
                env=os.environ | (env or {}),
                **kwargs,
            )
        except subprocess.CalledProcessError as exc:
            print("/n".join([exc.stdout, exc.stderr]))
            raise
        return call.stdout

    return _


@pytest.fixture
def cd(tmp_path: pathlib.Path):
    curdir = os.getcwd()

    def _(path: str):
        full_path = tmp_path / path
        full_path.mkdir()
        os.chdir(full_path)
        return full_path

    yield _
    os.chdir(curdir)


@pytest.fixture
def gh_config_dir(tmp_path: pathlib.Path):
    return str(tmp_path / "gh_config")


@pytest.fixture
def token_user_1():
    if "COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_1" not in os.environ:
        pytest.skip(
            "requires COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_1 in environment variables"
        )
    return os.environ["COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_1"]


@pytest.fixture
def token_user_2():
    if "COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_2" not in os.environ:
        pytest.skip(
            "requires COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_2 in environment variables"
        )
    return os.environ["COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_2"]


@pytest.fixture
def gh(call, gh_config_dir, token_user_1):
    def _gh(*args, token, json=False):
        stdout = call(
            "gh",
            *args,
            env={
                "GH_CONFIG_DIR": gh_config_dir,
                "GH_TOKEN": token,
                "NO_COLOR": "1",
            },
        )
        if stdout and json:
            return json_module.loads(stdout)
        else:
            return stdout

    # Default protocol is https so no need to change it but if we had to,
    # it would be here.
    # The following line may have an impact on users global git config
    # if they run the tests locally but it's unlikely to be problematic
    # Also, it's sad that gh requires a token for setup-git but meh.
    _gh("auth", "setup-git", token=token_user_1)
    return _gh


@pytest.fixture
def git(call, gh_config_dir):
    def _(*args, env=None):
        return call(
            "git",
            *args,
            env={
                "GH_CONFIG_DIR": gh_config_dir,
                "GIT_AUTHOR_NAME": "Foo",
                "GIT_AUTHOR_EMAIL": "foo@example.com",
            }
            | (env or {}),
        )

    return _


@pytest.fixture
def gh_me(gh, token_user_1):
    def _(*args, **kwargs):
        return gh(*args, token=token_user_1, **kwargs)

    return _


@pytest.fixture
def gh_me_username(gh_me):
    return gh_me("api", "/user", "--jq", ".login")


@pytest.fixture
def gh_other(gh, token_user_2):
    def _(*args, **kwargs):
        return gh(*args, token=token_user_2, **kwargs)

    return _


@pytest.fixture
def git_repo(cd, git):
    repo = cd("repo")
    git("init")
    shutil.copytree(
        pathlib.Path(__file__).parents[2] / "end_to_end_tests_repo",
        repo,
        dirs_exist_ok=True,
    )
    git("add", ".")
    git(
        "commit",
        "-m",
        "initial commit",
    )
    return repo


@pytest.fixture
def repo_name():
    # TODO: should this depend on request.node.name ?
    return "end_to_end_python_coverage_comment_action"


@pytest.fixture
def gh_repo(gh_me, git_repo, clean_gh_after_test, repo_name):
    try:
        gh_me("repo", "delete", repo_name, "--confirm")
    except subprocess.CalledProcessError:
        pass

    gh_me(
        "repo",
        "create",
        repo_name,
        "--push",
        f"--source={git_repo}",
        "--public",
    )

    yield git_repo
    if clean_gh_after_test:
        gh_me("repo", "delete", repo_name, "--confirm")


@pytest.fixture
def gh_fork(cd, gh_other, gh_me_username, git_repo, clean_gh_after_test, repo_name):
    cd("fork")
    gh_other("repo", "fork", f"{gh_me_username}/{repo_name}")

    yield

    if clean_gh_after_test:
        gh_other("repo", "delete", repo_name, "--confirm")


@pytest.fixture
def head_sha1(git):
    def _():
        return git("rev-parse", "HEAD").strip()

    return _


@pytest.fixture
def wait_for_run_to_start():
    def _(sha1, branch, gh):
        for _ in range(60):
            run = gh(
                "run",
                "list",
                "-b",
                branch,
                "-L",
                "1",
                "--json",
                "databaseId,headSha",
                json=True,
            )
            if not run:
                print("No GitHub Action run recorded. Waiting.")
                time.sleep(1)
                continue

            latest_run_sha1 = run[0]["headSha"]
            if latest_run_sha1 != sha1:
                print(
                    f"Latest run points to {latest_run_sha1}, expecting {sha1}. Waiting."
                )
                time.sleep(1)
                continue

            return run[0]["databaseId"]

        pytest.fail("Run didn't start within a minute. Stopping.")

    return _
