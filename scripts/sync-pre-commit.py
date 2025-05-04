#!/usr/bin/env python

# /// script
# dependencies = [
#   "ruamel.yaml",
# ]
# ///
# Usage: uv run scripts/sync-pre-commit.py
# or through pre-commit hook: pre-commit run --all-files sync-pre-commit

from __future__ import annotations

import contextlib
import copy
import pathlib
import subprocess
from collections.abc import Generator
from typing import Any, cast

import ruamel.yaml


@contextlib.contextmanager
def yaml_roundtrip(
    path: pathlib.Path,
) -> Generator[dict[str, Any], None, None]:
    yaml = ruamel.yaml.YAML()
    config = cast("dict[str, Any]", yaml.load(path.read_text()))
    old_config = copy.deepcopy(config)
    yield config
    if config != old_config:
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.dump(config, path)


def export_from_uv_lock(group_args):
    base_export_args = [
        "uv",
        "export",
        "--all-extras",
        "--no-hashes",
        "--no-header",
        "--no-emit-project",
        "--no-emit-workspace",
        "--no-annotate",
    ]
    packages = (
        subprocess.check_output(
            [*base_export_args, *group_args],
            text=True,
        )
        .strip()
        .split("\n")
    )
    print(packages)
    return packages


def main():
    groups_dev = [
        "--only-group=dev",
    ]
    dev_dependencies = export_from_uv_lock(groups_dev)
    dev_versions = dict(
        e.split(";")[0].strip().split("==", 1) for e in dev_dependencies
    )

    with yaml_roundtrip(pathlib.Path(".pre-commit-config.yaml")) as pre_commit_config:
        for repo in pre_commit_config["repos"]:
            project = repo["repo"].split("/")[-1]
            if project in dev_versions:
                repo["rev"] = f"v{dev_versions[project]}"


if __name__ == "__main__":
    main()
