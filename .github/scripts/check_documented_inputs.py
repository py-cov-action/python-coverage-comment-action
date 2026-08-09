"""Check that action.yml and the documentation agree on the action's inputs.

Two directions, because they rot differently:

1. Every input used in a docs/examples/ workflow must exist in action.yml. A
   typo here is invisible otherwise: GitHub Actions only logs an "Unexpected
   input(s)" warning, actionlint's input database is keyed by tag so it never
   fires on a SHA-pinned `uses:`, and zizmor doesn't look at inputs at all.

2. Every input in action.yml must appear in the README's "All options" block,
   which is meant to be exhaustive. USE_GH_PAGES_HTML_URL shipped in v3.36 and
   went undocumented for the best part of a year for want of this check.

Everything this reads is located by structure (a heading, a key), and a
checker that silently finds nothing is worse than no checker -- it reads as a
pass. So each lookup asserts it found something, and the script fails loudly
if the shape of action.yml or the README changes underneath it.
"""

from __future__ import annotations

import pathlib
import re
import sys
from typing import Any

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ACTION = ROOT / "action.yml"
README = ROOT / "README.md"
EXAMPLES = ROOT / "docs" / "examples"

ACTION_REPO = "py-cov-action/python-coverage-comment-action"
OPTIONS_HEADING = "### All options"


class CheckFailed(Exception):
    pass


def declared_inputs() -> set[str]:
    inputs = yaml.safe_load(ACTION.read_text()).get("inputs")
    if not inputs:
        raise CheckFailed(f"no inputs found in {ACTION.name}")
    return set(inputs)


def steps(workflow: dict[str, Any]):
    for job in (workflow.get("jobs") or {}).values():
        yield from job.get("steps") or []


def used_inputs() -> dict[str, set[str]]:
    """Inputs passed to this action, per example file."""
    used: dict[str, set[str]] = {}
    for path in sorted(EXAMPLES.rglob("*.yml")):
        workflow = yaml.safe_load(path.read_text())
        for step in steps(workflow):
            if not str(step.get("uses", "")).startswith(f"{ACTION_REPO}@"):
                continue
            keys = set(step.get("with") or {})
            if keys:
                used.setdefault(str(path.relative_to(ROOT)), set()).update(keys)
    if not used:
        raise CheckFailed(f"no {ACTION_REPO} step with inputs found under {EXAMPLES}")
    return used


def documented_inputs() -> set[str]:
    readme = README.read_text()
    _, _, after = readme.partition(f"\n{OPTIONS_HEADING}\n")
    if not after:
        raise CheckFailed(f"heading {OPTIONS_HEADING!r} not found in README.md")
    block = re.search(r"^```yaml.*?\n(.*?)^```$", after, re.DOTALL | re.MULTILINE)
    if not block:
        raise CheckFailed(f"no yaml block under {OPTIONS_HEADING!r}")
    documented = {
        key for step in yaml.safe_load(block[1]) for key in (step.get("with") or {})
    }
    if not documented:
        raise CheckFailed(f"no inputs listed under {OPTIONS_HEADING!r}")
    return documented


def main() -> int:
    try:
        declared = declared_inputs()
        used = used_inputs()
        documented = documented_inputs()
    except CheckFailed as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("(the check could not read what it expected; fix it)", file=sys.stderr)
        return 1

    failed = False
    for path, keys in used.items():
        if unknown := sorted(keys - declared):
            failed = True
            print(
                f"{path}: not an input of the action: {', '.join(unknown)}",
                file=sys.stderr,
            )

    if missing := sorted(declared - documented):
        failed = True
        print(
            f"README.md: {OPTIONS_HEADING!r} is missing: {', '.join(missing)}",
            file=sys.stderr,
        )
    if extra := sorted(documented - declared):
        failed = True
        print(
            f"README.md: {OPTIONS_HEADING!r} documents unknown inputs: {', '.join(extra)}",
            file=sys.stderr,
        )

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
