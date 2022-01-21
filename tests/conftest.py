import datetime

import pytest

from coverage_comment import coverage as coverage_module


@pytest.fixture
def coverage_json():
    return {
        "meta": {
            "version": "1.2.3",
            "timestamp": "2000-01-01T00:00:00",
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
                "missing_lines": [7, 9],
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


@pytest.fixture
def diff_coverage_json():

    return {
        "report_name": "XML",
        "diff_name": "master...HEAD, staged and unstaged changes",
        "src_stats": {
            "codebase/code.py": {
                "percent_covered": 80.0,
                "violation_lines": [9],
                "violations": [[9, None]],
            }
        },
        "total_num_lines": 5,
        "total_num_violations": 1,
        "total_percent_covered": 80,
        "num_changed_lines": 39,
    }


@pytest.fixture
def coverage_obj():
    return coverage_module.Coverage(
        meta=coverage_module.CoverageMetadata(
            version="1.2.3",
            timestamp=datetime.datetime(2000, 1, 1),
            branch_coverage=True,
            show_contexts=False,
        ),
        info=coverage_module.CoverageInfo(
            covered_lines=5,
            num_statements=6,
            percent_covered=0.75,
            missing_lines=1,
            excluded_lines=0,
            num_branches=2,
            num_partial_branches=1,
            covered_branches=1,
            missing_branches=1,
        ),
        files={
            "codebase/code.py": coverage_module.FileCoverage(
                path="codebase/code.py",
                executed_lines=[1, 2, 5, 6, 9],
                missing_lines=[7, 9],
                excluded_lines=[],
                info=coverage_module.CoverageInfo(
                    covered_lines=5,
                    num_statements=6,
                    percent_covered=0.75,
                    missing_lines=1,
                    excluded_lines=0,
                    num_branches=2,
                    num_partial_branches=1,
                    covered_branches=1,
                    missing_branches=1,
                ),
            )
        },
    )


@pytest.fixture
def coverage_obj_no_branch():
    return coverage_module.Coverage(
        meta=coverage_module.CoverageMetadata(
            version="1.2.3",
            timestamp=datetime.datetime(2000, 1, 1),
            branch_coverage=False,
            show_contexts=False,
        ),
        info=coverage_module.CoverageInfo(
            covered_lines=5,
            num_statements=6,
            percent_covered=0.75,
            missing_lines=1,
            excluded_lines=0,
            num_branches=None,
            num_partial_branches=None,
            covered_branches=None,
            missing_branches=None,
        ),
        files={
            "codebase/code.py": coverage_module.FileCoverage(
                path="codebase/code.py",
                executed_lines=[1, 2, 5, 6, 9],
                missing_lines=[7],
                excluded_lines=[],
                info=coverage_module.CoverageInfo(
                    covered_lines=5,
                    num_statements=6,
                    percent_covered=0.75,
                    missing_lines=1,
                    excluded_lines=0,
                    num_branches=None,
                    num_partial_branches=None,
                    covered_branches=None,
                    missing_branches=None,
                ),
            )
        },
    )


@pytest.fixture
def diff_coverage_obj():
    return coverage_module.DiffCoverage(
        total_num_lines=5,
        total_num_violations=1,
        total_percent_covered=0.8,
        num_changed_lines=39,
        files={
            "codebase/code.py": coverage_module.FileDiffCoverage(
                path="codebase/code.py",
                percent_covered=0.8,
                violation_lines=[7, 9],
            )
        },
    )
