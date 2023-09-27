import dataclasses
import datetime
import decimal
import json
import pathlib
from collections.abc import Iterable

from coverage_comment import log, subprocess


@dataclasses.dataclass
class CoverageMetadata:
    version: str
    timestamp: datetime.datetime
    branch_coverage: bool
    show_contexts: bool


@dataclasses.dataclass
class CoverageInfo:
    covered_lines: int
    num_statements: int
    percent_covered: decimal.Decimal
    missing_lines: int
    excluded_lines: int
    num_branches: int | None
    num_partial_branches: int | None
    covered_branches: int | None
    missing_branches: int | None


@dataclasses.dataclass
class FileCoverage:
    path: pathlib.Path
    executed_lines: list[int]
    missing_lines: list[int]
    excluded_lines: list[int]
    info: CoverageInfo


@dataclasses.dataclass
class Coverage:
    meta: CoverageMetadata
    info: CoverageInfo
    files: dict[pathlib.Path, FileCoverage]


# The format for Diff Coverage objects may seem a little weird, because it
# was originally copied from diff-cover schema. In order to keep the
# compatibility for existing custom template, we kept the same format.
# Maybe in v4, we can change it to a simpler format.


@dataclasses.dataclass
class FileDiffCoverage:
    path: pathlib.Path
    percent_covered: decimal.Decimal
    violation_lines: list[int]


@dataclasses.dataclass
class DiffCoverage:
    total_num_lines: int
    total_num_violations: int
    total_percent_covered: decimal.Decimal
    num_changed_lines: int
    files: dict[pathlib.Path, FileDiffCoverage]


def compute_coverage(num_covered: int, num_total: int) -> decimal.Decimal:
    if num_total == 0:
        return decimal.Decimal("1")
    return decimal.Decimal(num_covered) / decimal.Decimal(num_total)


def get_coverage_info(
    merge: bool, coverage_path: pathlib.Path
) -> tuple[dict, Coverage]:
    try:
        if merge:
            subprocess.run("coverage", "combine", path=coverage_path)

        json_coverage = json.loads(
            subprocess.run("coverage", "json", "-o", "-", path=coverage_path)
        )
    except subprocess.SubProcessError as exc:
        if "No source for code:" in str(exc):
            log.error(
                "Cannot read .coverage files because files are absolute. You need "
                "to configure coverage to write relative paths by adding the following "
                "option to your coverage configuration file:\n"
                "[run]\n"
                "relative_files = true\n\n"
                "Note that the specific format can be slightly different if you're using "
                "setup.cfg or pyproject.toml. See details in: "
                "https://coverage.readthedocs.io/en/6.2/config.html#config-run-relative-files"
            )
        raise

    return json_coverage, extract_info(data=json_coverage, coverage_path=coverage_path)


def generate_coverage_html_files(
    destination: pathlib.Path, coverage_path: pathlib.Path
) -> None:
    subprocess.run(
        "coverage",
        "html",
        "--skip-empty",
        "--directory",
        str(destination),
        path=coverage_path,
    )


def generate_coverage_markdown(coverage_path: pathlib.Path) -> str:
    return subprocess.run(
        "coverage",
        "report",
        "--format=markdown",
        "--show-missing",
        path=coverage_path,
    )


def extract_info(data: dict, coverage_path: pathlib.Path) -> Coverage:
    """
    {
        "meta": {
            "version": "5.5",
            "timestamp": "2021-12-26T22:27:40.683570",
            "branch_coverage": True,
            "show_contexts": False,
        },
        "files": {
            "codebase/code.py": {
                "executed_lines": [1, 2, 5, 6, 9],
                "summary": {
                    "covered_lines": 5,
                    "num_statements": 6,
                    "percent_covered": 75.0,
                    "missing_lines": 1,
                    "excluded_lines": 0,
                    "num_branches": 2,
                    "num_partial_branches": 1,
                    "covered_branches": 1,
                    "missing_branches": 1,
                },
                "missing_lines": [7],
                "excluded_lines": [],
            }
        },
        "totals": {
            "covered_lines": 5,
            "num_statements": 6,
            "percent_covered": 75.0,
            "missing_lines": 1,
            "excluded_lines": 0,
            "num_branches": 2,
            "num_partial_branches": 1,
            "covered_branches": 1,
            "missing_branches": 1,
        },
    }
    """
    return Coverage(
        meta=CoverageMetadata(
            version=data["meta"]["version"],
            timestamp=datetime.datetime.fromisoformat(data["meta"]["timestamp"]),
            branch_coverage=data["meta"]["branch_coverage"],
            show_contexts=data["meta"]["show_contexts"],
        ),
        files={
            coverage_path
            / path: FileCoverage(
                path=coverage_path / path,
                excluded_lines=file_data["excluded_lines"],
                executed_lines=file_data["executed_lines"],
                missing_lines=file_data["missing_lines"],
                info=CoverageInfo(
                    covered_lines=file_data["summary"]["covered_lines"],
                    num_statements=file_data["summary"]["num_statements"],
                    percent_covered=compute_coverage(
                        file_data["summary"]["covered_lines"]
                        + file_data["summary"].get("covered_branches", 0),
                        file_data["summary"]["num_statements"]
                        + file_data["summary"].get("num_branches", 0),
                    ),
                    missing_lines=file_data["summary"]["missing_lines"],
                    excluded_lines=file_data["summary"]["excluded_lines"],
                    num_branches=file_data["summary"].get("num_branches"),
                    num_partial_branches=file_data["summary"].get(
                        "num_partial_branches"
                    ),
                    covered_branches=file_data["summary"].get("covered_branches"),
                    missing_branches=file_data["summary"].get("missing_branches"),
                ),
            )
            for path, file_data in data["files"].items()
        },
        info=CoverageInfo(
            covered_lines=data["totals"]["covered_lines"],
            num_statements=data["totals"]["num_statements"],
            percent_covered=compute_coverage(
                data["totals"]["covered_lines"]
                + data["totals"].get("covered_branches", 0),
                data["totals"]["num_statements"]
                + data["totals"].get("num_branches", 0),
            ),
            missing_lines=data["totals"]["missing_lines"],
            excluded_lines=data["totals"]["excluded_lines"],
            num_branches=data["totals"].get("num_branches"),
            num_partial_branches=data["totals"].get("num_partial_branches"),
            covered_branches=data["totals"].get("covered_branches"),
            missing_branches=data["totals"].get("missing_branches"),
        ),
    )


def get_diff_coverage_info(
    added_lines: dict[pathlib.Path, list[int]], coverage: Coverage
) -> DiffCoverage:
    files = {}
    total_num_lines = 0
    total_num_violations = 0
    num_changed_lines = 0

    for path, added_lines_for_file in added_lines.items():
        num_changed_lines += len(added_lines_for_file)

        try:
            file = coverage.files[path]
        except KeyError:
            continue

        executed = set(file.executed_lines) & set(added_lines_for_file)
        count_executed = len(executed)

        missing = set(file.missing_lines) & set(added_lines_for_file)
        count_missing = len(missing)
        # Even partially covered lines are considered as covered, no line
        # appears in both counts
        count_total = count_executed + count_missing

        total_num_lines += count_total
        total_num_violations += count_missing

        percent_covered = compute_coverage(
            num_covered=count_executed, num_total=count_total
        )

        files[path] = FileDiffCoverage(
            path=path,
            percent_covered=percent_covered,
            violation_lines=sorted(missing),
        )
    final_percentage = compute_coverage(
        num_covered=total_num_lines - total_num_violations,
        num_total=total_num_lines,
    )

    return DiffCoverage(
        total_num_lines=total_num_lines,
        total_num_violations=total_num_violations,
        total_percent_covered=final_percentage,
        num_changed_lines=num_changed_lines,
        files=files,
    )


def get_added_lines(
    git: subprocess.Git, base_ref: str
) -> dict[pathlib.Path, list[int]]:
    # --unified=0 means we don't get any context lines for chunk, and we
    # don't merge chunks. This means the headers that describe line number
    # are always enough to derive what line numbers were added.
    git.fetch("origin", base_ref, "--depth=1000")
    diff = git.diff("--unified=0", "FETCH_HEAD", "--", ".")
    return parse_diff_output(diff)


def parse_diff_output(diff: str) -> dict[pathlib.Path, list[int]]:
    current_file: pathlib.Path | None = None
    added_filename_prefix = "+++ b/"
    result: dict[pathlib.Path, list[int]] = {}
    for line in diff.splitlines():
        if line.startswith(added_filename_prefix):
            current_file = pathlib.Path(line.removeprefix(added_filename_prefix))
            continue
        if line.startswith("@@"):
            lines = parse_line_number_diff_line(line)
            if len(lines) > 0:
                if current_file is None:
                    raise ValueError(f"Unexpected diff output format: \n{diff}")
                result.setdefault(current_file, []).extend(lines)

    return result


def parse_line_number_diff_line(line: str) -> Iterable[int]:
    """
    Parse the "added" part of the line number diff text:
        @@ -60,0 +61 @@ def compute_files(  -> [61]
        @@ -60,0 +61,3 @@ def compute_files(  -> [61, 62, 63]
    """
    start, length = (int(i) for i in (line.split()[2][1:] + ",1").split(",")[:2])
    return range(start, start + length)
