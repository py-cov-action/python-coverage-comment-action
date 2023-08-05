import contextlib
import functools
import json as json_module
import logging
import os
import pathlib
import re
import shutil
import subprocess
import time

import pytest
import tenacity

# In this directory, `gh` is not the global `gh` fixture, but is instead
# a fixture letting you use the `gh` CLI tool.

SLEEP_AFTER_API_CALL = 1  # second(s)


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
            print("\n".join([exc.stdout, exc.stderr]))
            raise
        return call.stdout

    return _


@contextlib.contextmanager
def _cd(tmp_path: pathlib.Path, path: str):
    full_path = tmp_path / path
    full_path.mkdir(exist_ok=True, parents=True)
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
def action_ref():
    return os.environ.get("COVERAGE_COMMENT_E2E_ACTION_REF", "v3")


@pytest.fixture
def _gh(call, gh_config_dir):
    def gh(*args, token, json=False, fail_value=None):
        @tenacity.retry(
            reraise=True,
            retry=(
                tenacity.retry_if_result(
                    lambda x: fail_value is not None and x == fail_value
                )
                | tenacity.retry_if_exception_type()
            ),
            stop=tenacity.stop_after_attempt(5),
            wait=tenacity.wait_incrementing(start=0, increment=5),
            after=tenacity.after_log(logging.getLogger(), logging.DEBUG),
        )
        def f():
            stdout = call(
                "gh",
                *(f"{e}" for e in args),
                env={
                    "GH_CONFIG_DIR": gh_config_dir,
                    "GH_TOKEN": token,
                    "NO_COLOR": "1",
                },
            )

            # Giving GitHub an opportunity to synchronize all their systems
            # (without that, we get random failures sometimes)
            time.sleep(SLEEP_AFTER_API_CALL)

            if stdout and json:
                return json_module.loads(stdout)
            else:
                return stdout

        return f()

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
def git_repo(cd, git, action_ref, code_path, subproject_id):
    with cd("repo") as repo:
        git("init", "-b", "main")
        # Copy .github
        shutil.copytree(
            pathlib.Path(__file__).parent / "repo" / ".github",
            repo / ".github",
            dirs_exist_ok=True,
        )
        # Copy everything else
        shutil.copytree(
            pathlib.Path(__file__).parent / "repo",
            repo / code_path,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".github"),
        )
        # Rewrite the specific version of the action we run in the workflow files.
        for file in (repo / ".github/workflows").iterdir():
            content = (
                file.read_text()
                .replace("__ACTION_REF__", action_ref)
                .replace("__ACTION_COVERAGE_PATH__", str(code_path))
                .replace("__ACTION_SUBPROJECT_ID__", str(subproject_id))
            )
            file.write_text(content)

        git("add", ".")
        git("commit", "-m", "initial commit")
        yield repo


@pytest.fixture
def repo_name(request):
    name = "python-coverage-comment-action-end-to-end"
    if suffix := os.getenv("COVERAGE_COMMENT_E2E_REPO_SUFFIX"):
        suffix = re.sub(r"[^A-Za-z0-9_.-]", "-", suffix)
        name += f"-{suffix}"
    mark = request.node.get_closest_marker("repo_suffix")
    if mark is not None:
        name = f"{name}-{'-'.join(mark.args)}"
    return name


@pytest.fixture
def code_path(request):
    mark = request.node.get_closest_marker("code_path")
    return pathlib.Path(*mark.args) if mark else pathlib.Path(".")


@pytest.fixture
def subproject_id(request):
    mark = request.node.get_closest_marker("subproject_id")
    return mark.args[0] if mark else None


@pytest.fixture
def repo_full_name(repo_name, gh_me_username):
    return f"{gh_me_username}/{repo_name}"


@pytest.fixture
def gh_delete_repo(repo_name):
    def f(gh):
        try:
            print(f"Deleting repository {repo_name}")
            gh("repo", "delete", repo_name, "--yes")
        except subprocess.CalledProcessError:
            pass

    return f


@pytest.fixture
def gh_create_repo(is_failed, gh_delete_repo, gh_me, git_repo, repo_name):
    gh_delete_repo(gh_me)

    def f(*args):
        print(f"Creating repository {repo_name}")
        gh_me(
            "repo",
            "create",
            repo_name,
            "--push",
            f"--source={git_repo}",
            *args,
        )
        # Someday, we may be able to change that to a variable instead of a secret
        # https://github.com/cli/cli/pull/6928
        gh_me(
            "secret",
            "set",
            "--app=actions",
            "ACTIONS_STEP_DEBUG",
            "--body=true",
        )
        return git_repo

    return f


@pytest.fixture
def gh_create_fork(is_failed, gh_delete_repo, gh_other, gh_me_username, repo_name):
    # (can only be called after the main repo has been created)
    gh_delete_repo(gh_other)

    def f():
        # -- . at the end is because we want to clone in the current dir
        # (args after -- are passed to git clone)
        print(f"Forking repository {gh_me_username}/{repo_name}")
        gh_other("repo", "fork", "--clone", f"{gh_me_username}/{repo_name}", "--", ".")

    yield f


@pytest.fixture
def get_sha1(git):
    def _(spec="HEAD"):
        return git("rev-parse", spec).strip()

    return _


@pytest.fixture
def wait_for_run_to_start():
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(60),
        wait=tenacity.wait_fixed(1),
        reraise=True,
    )
    def _(*, sha1, branch, gh):
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
            print("No GitHub Action run recorded.")
            raise tenacity.TryAgain()

        latest_run_sha1 = run[0]["headSha"]
        if latest_run_sha1 != sha1:
            print(f"Latest run points to {latest_run_sha1}, expecting {sha1}.")
            raise tenacity.TryAgain()

        return run[0]["databaseId"]

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
def add_coverage_line(git, code_path):
    def f(line):
        csv_file = pathlib.Path(code_path / "tests/cases.csv")
        csv_file.write_text(csv_file.read_text() + line + "\n")

        git("add", str(csv_file))
        git("commit", "-m", "improve coverage")

    return f
