"""Sync the workflow examples in docs/examples/ into the README.

The files under docs/examples/ are the source of truth: they're real workflows,
so zizmor lints them and renovate keeps their `uses:` pins current. The README
only holds a copy, marked up as:

    ```yaml title="docs/examples/basic-usage/ci.yml"

GitHub renders that fence exactly like a plain ```yaml one -- everything after
the language is dropped -- so the marker is invisible in the rendered README.

Add `lines=` to show only part of a file, for snippets that would be noise as a
whole workflow:

    ```yaml title="docs/examples/enforce-coverage/ci.yml" lines=24-31

Line numbers do drift when the example is edited. The sync rewrites the README
in the same commit, so drift shows up as a README diff rather than silently;
on top of that a slice must start on a `- ` step, which catches a range that
has slid into the middle of a mapping.

Run with --check to fail instead of rewriting (the pre-commit hook rewrites,
which lets autofix.ci push the result).
"""

from __future__ import annotations

import argparse
import difflib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
README = ROOT / "README.md"
EXAMPLES = ROOT / "docs" / "examples"

BLOCK = re.compile(
    r'^```yaml title="(?P<path>[^"]+)"(?P<lines> lines=(?P<start>\d+)-(?P<end>\d+))?\n'
    r"(?P<body>.*?)^```$",
    re.DOTALL | re.MULTILINE,
)


def slice_lines(path: str, text: str, start: int, end: int) -> str:
    lines = text.splitlines(keepends=True)
    if not 1 <= start <= end <= len(lines):
        raise SystemExit(
            f"{path} has {len(lines)} lines, but the README asks for {start}-{end}"
        )
    excerpt = lines[start - 1 : end]
    first = next((line for line in excerpt if line.strip()), "")
    if not first.lstrip().startswith("- "):
        raise SystemExit(
            f"{path} lines {start}-{end} start mid-step ({first.strip()!r}); "
            f"the range has probably drifted"
        )
    return "".join(excerpt)


def sync(readme: str) -> tuple[str, list[str]]:
    seen: list[str] = []

    def replace(match: re.Match[str]) -> str:
        path = match["path"]
        source = ROOT / path
        if not source.is_file():
            raise SystemExit(f"README references {path}, which does not exist")
        seen.append(path)
        text = source.read_text()
        if match["lines"]:
            text = slice_lines(path, text, int(match["start"]), int(match["end"]))
        return f'```yaml title="{path}"{match["lines"] or ""}\n{text}```'

    return BLOCK.sub(replace, readme), seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail instead of rewriting"
    )
    args = parser.parse_args()

    original = README.read_text()
    updated, seen = sync(original)

    # Every example must be shown somewhere, otherwise it silently rots.
    orphans = sorted(
        str(path.relative_to(ROOT))
        for path in EXAMPLES.rglob("*.yml")
        if str(path.relative_to(ROOT)) not in seen
    )
    if orphans:
        print("Not referenced by README.md: " + ", ".join(orphans), file=sys.stderr)
        return 1

    if updated == original:
        return 0

    if args.check:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile="README.md",
            tofile="README.md (synced)",
        )
        sys.stderr.writelines(diff)
        print(
            "\nREADME.md is out of sync; run .github/scripts/sync_readme_examples.py",
            file=sys.stderr,
        )
        return 1

    README.write_text(updated)
    print("Updated README.md")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
