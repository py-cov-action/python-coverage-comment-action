import dataclasses
import datetime
import json
import pathlib
import subprocess
import tempfile


def call(*args, **kwargs):
    return subprocess.run(
        args,
        text=True,
        check=True,
        capture_output=True,
        **kwargs,
    )


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
    num_branches: int
    num_partial_branches: int
    covered_branches: int
    missing_branches: int


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
    if merge:
        call("coverage", "combine")

    call("coverage", "json")
    call("coverage", "xml")

    return extract_info(read_json(file=pathlib.Path("coverage.json")))


def read_json(file: pathlib.Path):
    json.loads(file.read_text())


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
            branch_coverage=data["meta"]["branchcoverage"],
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
                    num_branches=file_data["summary"]["num_branches"],
                    num_partial_branches=file_data["summary"]["num_partial_branches"],
                    covered_branches=file_data["summary"]["covered_branches"],
                    missing_branches=file_data["summary"]["missing_branches"],
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
            num_branches=data["totals"]["num_branches"],
            num_partial_branches=data["totals"]["num_partial_branches"],
            covered_branches=data["totals"]["covered_branches"],
            missing_branches=data["totals"]["missing_branches"],
        ),
    )


def get_diff_coverage_info(base_ref: str) -> DiffCoverage:
    call("git", "fetch", "--depth=1000")
    with tempfile.NamedTemporaryFile("r") as f:
        call(
            "diff-cover",
            "coverage.xml",
            f"--compare-branch=origin/{base_ref}",
            f"--json-report={f.name}",
            "--diff-range-notation=..",
            "--quiet",
        )
        return extract_diff_info(read_json(file=pathlib.Path(f.name)))


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
        total_percent_covered=data["total_percent_covered"],
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
