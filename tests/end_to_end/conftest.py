import contextlib
import functools
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


@contextlib.contextmanager
def _cd(tmp_path: pathlib.Path, path: str):
    full_path = tmp_path / path
    full_path.mkdir(exist_ok=True)
    old_path = pathlib.Path.cwd()
    if old_path == full_path:
        yield full_path
        return
    os.chdir(full_path)
    try:
        yield full_path
    finally:
        os.chdir(old_path)


@pytest.fixture
def cd(tmp_path: pathlib.Path):
    init_path = os.getcwd()
    yield functools.partial(_cd, tmp_path)
    os.chdir(init_path)


@pytest.fixture
def gh_config_dir(tmp_path: pathlib.Path):
    return str(tmp_path / "gh_config")


@pytest.fixture
def token_me():
    if not os.environ.get("COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_1"):
        pytest.skip(
            "requires COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_1 in environment variables"
        )
    return os.environ["COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_1"]


@pytest.fixture
def token_other():
    if not os.environ.get("COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_2"):
        pytest.skip(
            "requires COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_2 in environment variables"
        )
    return os.environ["COVERAGE_COMMENT_E2E_GITHUB_TOKEN_USER_2"]


@pytest.fixture
def _gh(call, gh_config_dir):
    def gh(*args, token, json=False):
        stdout = call(
            "gh",
            *(f"{e}" for e in args),
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

    return gh


@pytest.fixture
def gh(setup_git, _gh):
    return _gh


@pytest.fixture
def setup_git(git, _gh, token_me):
    # Default protocol is https so no need to change it but if we had to,
    # it would be here.
    # The following line may have an impact on users global git config
    # if they run the tests locally but it's unlikely to be problematic
    # Also, it's sad that gh requires a token for setup-git but meh.
    _gh("auth", "setup-git", token=token_me)

    # Special step just because CircleCI's configuration breaks otherwise
    if "CIRCLECI" in os.environ:
        git("config", "--global", "--remove-section", "url.ssh://git@github.com")


@pytest.fixture
def git(call, gh_config_dir):
    def f(*args, env=None):
        return call(
            "git",
            *args,
            env={
                "GH_CONFIG_DIR": gh_config_dir,
                "GIT_AUTHOR_NAME": "Foo",
                "GIT_AUTHOR_EMAIL": "foo@example.com",
                "GIT_COMMITTER_NAME": "Foo",
                "GIT_COMMITTER_EMAIL": "foo@example.com",
            }
            | (env or {}),
        )

    return f


@pytest.fixture
def gh_me(gh, cd, token_me):
    def f(*args, **kwargs):
        with cd("repo"):
            return gh(*args, token=token_me, **kwargs)

    return f


@pytest.fixture
def gh_me_username(gh_me):
    return gh_me("api", "/user", "--jq", ".login").strip()


@pytest.fixture
def gh_other(gh, cd, token_other):
    def f(*args, **kwargs):
        with cd("fork"):
            return gh(*args, token=token_other, **kwargs)

    return f


@pytest.fixture
def gh_other_username(gh_other):
    return gh_other("api", "/user", "--jq", ".login").strip()


@pytest.fixture
def git_repo(cd, git):
    with cd("repo") as repo:
        git("init")
        shutil.copytree(
            pathlib.Path(__file__).parents[2] / "end_to_end_tests_repo",
            repo,
            dirs_exist_ok=True,
        )
        git("add", ".")
        git("commit", "-m", "initial commit")
        yield repo


@pytest.fixture
def repo_name():
    # TODO: should this depend on request.node.name ?
    return "python-coverage-comment-action-end-to-end"


@pytest.fixture
def repo_full_name(repo_name, gh_me_username):
    return f"{gh_me_username}/{repo_name}"


@pytest.fixture
def gh_create_repo(gh_me, git_repo, repo_name):
    try:
        gh_me("repo", "delete", repo_name, "--confirm")
    except subprocess.CalledProcessError:
        pass

    def f(*args):

        gh_me(
            "repo",
            "create",
            repo_name,
            "--push",
            f"--source={git_repo}",
            *args,
        )
        return git_repo

    return f


@pytest.fixture
def gh_create_fork(gh_other, gh_me_username, repo_name):
    # (can only be called after the main repo has been created)
    try:
        gh_other("repo", "delete", repo_name, "--confirm")
    except subprocess.CalledProcessError:
        pass

    def f():
        # -- . at the end is because we want to clone in the current dir
        # (args after -- are passed to git clone)
        gh_other("repo", "fork", "--clone", f"{gh_me_username}/{repo_name}", "--", ".")

    return f


@pytest.fixture
def head_sha1(git):
    def _():
        return git("rev-parse", "HEAD").strip()

    return _


@pytest.fixture
def wait_for_run_to_start():
    def _(*, sha1, branch, gh):
        for _ in range(60):
            run = gh(
                "run",
                "list",
                "--branch",
                branch,
                "--limit",
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


@pytest.fixture
def wait_for_run_triggered_by_user_to_start():
    def _(*, workflow_name, triggering_user, gh):
        for _ in range(60):
            payload = gh("api", "/repos/{owner}/{repo}/actions/runs", json=True)
            runs = payload["workflow_runs"]
            if not runs:
                print("No GitHub Action run recorded. Waiting.")
                time.sleep(1)
                continue

            run = runs[0]
            run_name = run["name"]
            run_triggering_actor = run["triggering_actor"]["login"]
            if run_name != workflow_name or run_triggering_actor != triggering_user:
                print(
                    f'Latest run is on workflow "{run_name}", '
                    f"triggered by {run_triggering_actor}. Waiting."
                )
                time.sleep(1)
                continue

            return run["id"]

        pytest.fail("Run didn't start within a minute. Stopping.")

    return _


@pytest.fixture
def add_coverage_line(git):
    def f(line):
        csv_file = pathlib.Path("tests/cases.csv")
        csv_file.write_text(csv_file.read_text() + line)

        git("add", str(csv_file))
        git("commit", "-m", "improve coverage")

    return f
