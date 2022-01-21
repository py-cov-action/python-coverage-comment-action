import dataclasses
import datetime
import json
import pathlib
import tempfile

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
    percent_covered: float
    missing_lines: int
    excluded_lines: int
    num_branches: int | None
    num_partial_branches: int | None
    covered_branches: int | None
    missing_branches: int | None


@dataclasses.dataclass
class FileCoverage:
    path: str
    executed_lines: list[int]
    missing_lines: list[int]
    excluded_lines: list[int]
    info: CoverageInfo


@dataclasses.dataclass
class Coverage:
    meta: CoverageMetadata
    info: CoverageInfo
    files: dict[str, FileCoverage]


@dataclasses.dataclass
class FileDiffCoverage:
    path: str
    percent_covered: float
    violation_lines: list[int]


@dataclasses.dataclass
class DiffCoverage:
    total_num_lines: int
    total_num_violations: int
    total_percent_covered: float
    num_changed_lines: int
    files: dict[pathlib.Path, FileDiffCoverage]


def get_coverage_info(merge: bool) -> Coverage:
    try:
        if merge:
            subprocess.run("coverage", "combine")

        json_coverage = subprocess.run("coverage", "json", "-o", "-")
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

    return extract_info(json.loads(json_coverage))


def extract_info(data) -> Coverage:
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
            path: FileCoverage(
                path=path,
                excluded_lines=file_data["excluded_lines"],
                executed_lines=file_data["executed_lines"],
                missing_lines=file_data["missing_lines"],
                info=CoverageInfo(
                    covered_lines=file_data["summary"]["covered_lines"],
                    num_statements=file_data["summary"]["num_statements"],
                    percent_covered=file_data["summary"]["percent_covered"] / 100,
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
            percent_covered=data["totals"]["percent_covered"] / 100,
            missing_lines=data["totals"]["missing_lines"],
            excluded_lines=data["totals"]["excluded_lines"],
            num_branches=data["totals"].get("num_branches"),
            num_partial_branches=data["totals"].get("num_partial_branches"),
            covered_branches=data["totals"].get("covered_branches"),
            missing_branches=data["totals"].get("missing_branches"),
        ),
    )


def get_diff_coverage_info(base_ref: str) -> DiffCoverage:
    subprocess.run("git", "fetch", "--depth=1000")
    subprocess.run("coverage", "xml")
    with tempfile.NamedTemporaryFile("r") as f:
        subprocess.run(
            "diff-cover",
            "coverage.xml",
            f"--compare-branch=origin/{base_ref}",
            f"--json-report={f.name}",
            "--diff-range-notation=..",
            "--quiet",
        )
        diff_json = json.loads(pathlib.Path(f.name).read_text())

    return extract_diff_info(diff_json)


def extract_diff_info(data) -> DiffCoverage:
    """
    {
        "report_name": "XML",
        "diff_name": "master...HEAD, staged and unstaged changes",
        "src_stats": {
            "codebase/code.py": {
                "percent_covered": 80.0,
                "violation_lines": [9],
                "violations": [[9, null]],
            }
        },
        "total_num_lines": 5,
        "total_num_violations": 1,
        "total_percent_covered": 80,
        "num_changed_lines": 39,
    }
    """
    return DiffCoverage(
        total_num_lines=data["total_num_lines"],
        total_num_violations=data["total_num_violations"],
        total_percent_covered=data["total_percent_covered"] / 100,
        num_changed_lines=data["num_changed_lines"],
        files={
            path: FileDiffCoverage(
                path=path,
                percent_covered=file_data["percent_covered"] / 100,
                violation_lines=file_data["violation_lines"],
            )
            for path, file_data in data["src_stats"].items()
        },
    )
