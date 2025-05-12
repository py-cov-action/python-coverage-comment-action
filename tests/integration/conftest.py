from __future__ import annotations

import os
import pathlib
import subprocess
import uuid

import pytest


@pytest.fixture
def in_integration_env(integration_env, integration_dir):
    curdir = os.getcwd()
    os.chdir(integration_dir)
    yield integration_dir
    os.chdir(curdir)


@pytest.fixture
def integration_dir(tmp_path: pathlib.Path):
    test_dir = tmp_path / "integration_test"
    test_dir.mkdir()
    return test_dir


@pytest.fixture
def file_path(integration_dir):
    return integration_dir / "foo.py"


@pytest.fixture
def write_file(file_path):
    def _(*variables):
        content = "import os"
        for i, var in enumerate(variables):
            content += f"""\nif os.environ.get("{var}"):\n    {i}\n"""
        file_path.write_text(content, encoding="utf8")

    return _


@pytest.fixture
def run_coverage(file_path, integration_dir):
    def _(*variables):
        subprocess.check_call(
            ["coverage", "run", "--parallel", file_path.name],
            cwd=integration_dir,
            env=os.environ | dict.fromkeys(variables, "1"),
        )

    return _


@pytest.fixture
def commit(integration_dir):
    def _():
        subprocess.check_call(
            ["git", "add", "."],
            cwd=integration_dir,
        )
        subprocess.check_call(
            ["git", "commit", "-m", str(uuid.uuid4())],
            cwd=integration_dir,
            env={
                "GIT_AUTHOR_NAME": "foo",
                "GIT_AUTHOR_EMAIL": "foo",
                "GIT_COMMITTER_NAME": "foo",
                "GIT_COMMITTER_EMAIL": "foo",
                "GIT_CONFIG_GLOBAL": "/dev/null",
                "GIT_CONFIG_SYSTEM": "/dev/null",
            },
        )

    return _


@pytest.fixture
def integration_env(integration_dir, write_file, run_coverage, commit, request):
    subprocess.check_call(["git", "init", "-b", "main"], cwd=integration_dir)
    # diff coverage reads the "origin/{...}" branch so we simulate an origin remote
    subprocess.check_call(["git", "remote", "add", "origin", "."], cwd=integration_dir)
    write_file("A", "B")
    commit()

    add_branch_mark = request.node.get_closest_marker("add_branches")
    for additional_branch in add_branch_mark.args if add_branch_mark else []:
        subprocess.check_call(
            ["git", "switch", "-c", additional_branch],
            cwd=integration_dir,
        )

    subprocess.check_call(
        ["git", "switch", "-c", "branch"],
        cwd=integration_dir,
    )

    write_file("A", "B", "C", "D")
    commit()

    run_coverage("A", "C")
    subprocess.check_call(["git", "fetch", "origin"], cwd=integration_dir)
