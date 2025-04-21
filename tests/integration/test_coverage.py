from __future__ import annotations

import subprocess
from coverage_comment import coverage, subprocess as subprocess_module


def test_get_added_lines(
    commit, file_path, integration_dir, in_integration_env, write_file
):
    """
    Lines added in the base_ref should not appear as added in HEAD
    """
    git = subprocess_module.Git()
    relative_file_path = file_path.relative_to(integration_dir)

    def _check_added_lines():
        added_lines = coverage.get_added_lines(git, "main")

        assert added_lines == {
            relative_file_path: list(range(7, 13))  # Line numbers start at 1
        }

    _check_added_lines()
    subprocess.check_call(["git", "switch", "main"], cwd=integration_dir)
    write_file("E", "F")
    commit()
    subprocess.check_call(["git", "push", "origin", "main"], cwd=integration_dir)
    subprocess.check_call(["git", "switch", "branch"], cwd=integration_dir)

    _check_added_lines()
