import decimal
import json
import pathlib

import pytest

from coverage_comment import coverage, subprocess


@pytest.mark.parametrize(
    "num_covered, num_total, expected_coverage",
    [
        (0, 10, "0"),
        (0, 0, "1"),
        (5, 0, "1"),
        (5, 10, "0.5"),
        (1, 100, "0.01"),
    ],
)
def test_compute_coverage(num_covered, num_total, expected_coverage):
    assert coverage.compute_coverage(num_covered, num_total) == decimal.Decimal(
        expected_coverage
    )


def test_get_coverage_info(mocker, coverage_json, coverage_obj):
    run = mocker.patch(
        "coverage_comment.subprocess.run", return_value=json.dumps(coverage_json)
    )

    raw_coverage_information, result = coverage.get_coverage_info(
        merge=True, coverage_path=pathlib.Path(".")
    )

    assert run.call_args_list == [
        mocker.call("coverage", "combine", path=pathlib.Path(".")),
        mocker.call("coverage", "json", "-o", "-", path=pathlib.Path(".")),
    ]

    assert result == coverage_obj
    assert raw_coverage_information == coverage_json


def test_get_coverage_info__no_merge(mocker, coverage_json):
    run = mocker.patch(
        "coverage_comment.subprocess.run", return_value=json.dumps(coverage_json)
    )

    coverage.get_coverage_info(merge=False, coverage_path=pathlib.Path("."))

    assert (
        mocker.call("coverage", "combine", path=pathlib.Path("."))
        not in run.call_args_list
    )


def test_get_coverage_info__error_base(mocker, get_logs):
    mocker.patch(
        "coverage_comment.subprocess.run", side_effect=subprocess.SubProcessError
    )

    with pytest.raises(subprocess.SubProcessError):
        coverage.get_coverage_info(merge=False, coverage_path=pathlib.Path("."))

    assert not get_logs("ERROR")


def test_get_coverage_info__error_no_source(mocker, get_logs):
    mocker.patch(
        "coverage_comment.subprocess.run",
        side_effect=subprocess.SubProcessError("No source for code: bla"),
    )

    with pytest.raises(subprocess.SubProcessError):
        coverage.get_coverage_info(merge=False, coverage_path=pathlib.Path("."))

    assert get_logs("ERROR", "Cannot read")


def test_generate_coverage_html_files(mocker):
    run = mocker.patch(
        "coverage_comment.subprocess.run",
    )

    coverage.generate_coverage_html_files(
        destination=pathlib.Path("/tmp/foo"), coverage_path=pathlib.Path(".")
    )

    assert run.call_args_list == [
        mocker.call(
            "coverage",
            "html",
            "--skip-empty",
            "--directory",
            "/tmp/foo",
            path=pathlib.Path("."),
        ),
    ]


def test_generate_coverage_markdown(mocker):
    run = mocker.patch("coverage_comment.subprocess.run", return_value="foo")

    result = coverage.generate_coverage_markdown(coverage_path=pathlib.Path("."))

    assert run.call_args_list == [
        mocker.call(
            "coverage",
            "report",
            "--format=markdown",
            "--show-missing",
            path=pathlib.Path("."),
        ),
    ]

    assert result == "foo"


@pytest.mark.parametrize(
    "added_lines, executed_lines, missing_lines, expected",
    [
        (
            {pathlib.Path("codebase/code.py"): [1, 3]},
            [1, 2],
            [3],
            coverage.DiffCoverage(
                total_num_lines=2,
                total_num_violations=1,
                total_percent_covered=decimal.Decimal("0.5"),
                num_changed_lines=2,
                files={
                    pathlib.Path("codebase/code.py"): coverage.FileDiffCoverage(
                        path=pathlib.Path("codebase/code.py"),
                        percent_covered=decimal.Decimal("0.5"),
                        violation_lines=[3],
                    )
                },
            ),
        ),
        (
            {pathlib.Path("codebase/code2.py"): [1, 3]},
            [1, 2],
            [3],
            coverage.DiffCoverage(
                total_num_lines=0,
                total_num_violations=0,
                total_percent_covered=decimal.Decimal("1"),
                num_changed_lines=2,
                files={},
            ),
        ),
        (
            {pathlib.Path("codebase/code.py"): [4, 5, 6]},
            [1, 2, 3],
            [7],
            coverage.DiffCoverage(
                total_num_lines=0,
                total_num_violations=0,
                total_percent_covered=decimal.Decimal("1"),
                num_changed_lines=3,
                files={
                    pathlib.Path("codebase/code.py"): coverage.FileDiffCoverage(
                        path=pathlib.Path("codebase/code.py"),
                        percent_covered=decimal.Decimal("1"),
                        violation_lines=[],
                    )
                },
            ),
        ),
    ],
)
def test_get_diff_coverage_info(
    coverage_obj_no_branch, added_lines, executed_lines, missing_lines, expected
):
    cov_file = coverage_obj_no_branch.files[pathlib.Path("codebase/code.py")]
    cov_file.executed_lines = executed_lines
    cov_file.missing_lines = missing_lines
    result = coverage.get_diff_coverage_info(
        added_lines=added_lines, coverage=coverage_obj_no_branch
    )
    assert result == expected


def test_get_added_lines(git):
    diff = (
        """+++ b/README.md\n@@ -1,2 +1,3 @@\n-# coverage-comment\n+coverage-comment\n"""
    )
    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD -- .")(stdout=diff)
    assert coverage.get_added_lines(git=git, base_ref="main") == {
        pathlib.Path("README.md"): [1, 2, 3]
    }


@pytest.mark.parametrize(
    "line_number_diff_line, expected",
    [
        ("@@ -1,2 +7,4 @@ foo()", [7, 8, 9, 10]),
        ("@@ -1,2 +8 @@ foo()", [8]),
    ],
)
def test_parse_line_number_diff_line(git, line_number_diff_line, expected):
    result = list(coverage.parse_line_number_diff_line(line_number_diff_line))
    assert result == expected


def test_parse_diff_output(git):
    diff = """diff --git a/README.md b/README.md
index 1f1d9a4..e69de29 100644
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-# coverage-comment
-coverage-comment
@@ -3,2 +3,4 @@
-foo
-bar
+foo1
+bar1
+foo2
+bar2
--- a/foo.txt
+++ b/foo.txt
@@ -0,0 +1 @@
+bar
"""
    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD -- .")(stdout=diff)
    assert coverage.parse_diff_output(diff=diff) == {
        pathlib.Path("README.md"): [1, 3, 4, 5, 6],
        pathlib.Path("foo.txt"): [1],
    }
