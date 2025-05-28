from __future__ import annotations

import decimal
import json
import pathlib

import pytest

from coverage_comment import coverage, subprocess


def test_diff_violations(make_coverage_and_diff):
    _, diff = make_coverage_and_diff(
        """
        # file: a.py
        + 1 missing
        2 missing
        + 3 missing
        4 covered
        + 5 covered
        """
    )
    assert diff.files[pathlib.Path("a.py")].violation_lines == [1, 3]


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


@pytest.mark.parametrize(
    "num_covered, num_total, branch_covered, branch_total, expected_coverage",
    [
        (0, 10, 0, 15, "0"),
        (0, 0, 0, 0, "1"),
        (5, 0, 5, 0, "1"),
        (5, 10, 5, 10, "0.5"),
        (1, 50, 1, 50, "0.02"),
    ],
)
def test_compute_coverage_with_branches(
    num_covered, num_total, branch_covered, branch_total, expected_coverage
):
    assert coverage.compute_coverage(
        num_covered, num_total, branch_covered, branch_total
    ) == decimal.Decimal(expected_coverage)


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


def test__make_coverage_info():
    result = coverage._make_coverage_info(
        {
            "covered_lines": 14,
            "num_statements": 20,
            "missing_lines": 6,
            "excluded_lines": 0,
        }
    )
    assert isinstance(result, coverage.CoverageInfo)
    assert result.percent_covered == decimal.Decimal(14) / decimal.Decimal(20)
    assert result.num_branches == 0
    assert result.num_partial_branches == 0
    assert result.covered_branches == 0
    assert result.missing_branches == 0


def test__make_coverage_info__with_branches():
    result = coverage._make_coverage_info(
        {
            "covered_lines": 4,
            "num_statements": 10,
            "missing_lines": 1,
            "excluded_lines": 0,
            "covered_branches": 4,
            "num_branches": 6,
            "num_partial_branches": 2,
        }
    )
    assert isinstance(result, coverage.CoverageInfo)
    assert result.percent_covered == decimal.Decimal(4 + 4) / decimal.Decimal(10 + 6)
    assert result.covered_branches == 4
    assert result.missing_branches == 0
    assert result.excluded_lines == 0


@pytest.mark.parametrize(
    "added_lines, update_obj, expected",
    [
        # A first simple example. We added lines 1 and 3 to a file. Coverage
        # info says that lines 1 and 2 were executed and line 3 was not.
        # Diff coverage should report that the violation is line 3 and
        # that the total coverage is 50%.
        (
            {pathlib.Path("codebase/code.py"): [1, 3]},
            {"codebase/code.py": {"executed_lines": [1, 2], "missing_lines": [3]}},
            coverage.DiffCoverage(
                total_num_lines=2,
                total_num_violations=1,
                total_percent_covered=decimal.Decimal("0.5"),
                num_changed_lines=2,
                files={
                    pathlib.Path("codebase/code.py"): coverage.FileDiffCoverage(
                        path=pathlib.Path("codebase/code.py"),
                        percent_covered=decimal.Decimal("0.5"),
                        added_statements=[1, 3],
                        covered_statements=[1],
                        missing_statements=[3],
                        added_lines=[1, 3],
                    )
                },
            ),
        ),
        # A second simple example. This time, the only modified file (code2.py)
        # is not the same as the files that received coverage info (code.py).
        # Consequently, no line should be reported as a violation (we could
        # imagine that the file code2.py only contains comments and is not
        # covered, nor imported.)
        (
            {pathlib.Path("codebase/code2.py"): [1, 3]},
            {"codebase/code.py": {"executed_lines": [1, 2], "missing_lines": [3]}},
            coverage.DiffCoverage(
                total_num_lines=0,
                total_num_violations=0,
                total_percent_covered=decimal.Decimal("1"),
                num_changed_lines=2,
                files={},
            ),
        ),
        # A third simple example. This time, there's no intersection between
        # the modified files and the files that received coverage info. We
        # should not report any violation (and 100% coverage)
        (
            {pathlib.Path("codebase/code.py"): [4, 5, 6]},
            {"codebase/code.py": {"executed_lines": [1, 2, 3], "missing_lines": [7]}},
            coverage.DiffCoverage(
                total_num_lines=0,
                total_num_violations=0,
                total_percent_covered=decimal.Decimal("1"),
                num_changed_lines=3,
                files={
                    pathlib.Path("codebase/code.py"): coverage.FileDiffCoverage(
                        path=pathlib.Path("codebase/code.py"),
                        percent_covered=decimal.Decimal("1"),
                        added_statements=[],
                        covered_statements=[],
                        missing_statements=[],
                        added_lines=[4, 5, 6],
                    )
                },
            ),
        ),
        # A more complex example with 2 distinct files. We want to check both
        # that they are individually handled correctly and that the general
        # stats are correct.
        (
            {
                pathlib.Path("codebase/code.py"): [4, 5, 6],
                pathlib.Path("codebase/other.py"): [10, 13],
            },
            {
                "codebase/code.py": {
                    "executed_lines": [1, 2, 3, 5, 6],
                    "missing_lines": [7],
                },
                "codebase/other.py": {
                    "executed_lines": [10, 11, 12],
                    "missing_lines": [13],
                },
            },
            coverage.DiffCoverage(
                total_num_lines=4,  # 2 lines in code.py + 2 lines in other.py
                total_num_violations=1,  # 1 line in other.py
                total_percent_covered=decimal.Decimal("0.75"),  # 3/4 lines covered
                num_changed_lines=5,  # 3 lines in code.py + 2 lines in other.py
                files={
                    pathlib.Path("codebase/code.py"): coverage.FileDiffCoverage(
                        path=pathlib.Path("codebase/code.py"),
                        percent_covered=decimal.Decimal("1"),
                        added_statements=[5, 6],
                        covered_statements=[5, 6],
                        missing_statements=[],
                        added_lines=[4, 5, 6],
                    ),
                    pathlib.Path("codebase/other.py"): coverage.FileDiffCoverage(
                        path=pathlib.Path("codebase/other.py"),
                        percent_covered=decimal.Decimal("0.5"),
                        added_statements=[10, 13],
                        covered_statements=[10],
                        missing_statements=[13],
                        added_lines=[10, 13],
                    ),
                },
            ),
        ),
    ],
)
def test_get_diff_coverage_info(make_coverage_obj, added_lines, update_obj, expected):
    result = coverage.get_diff_coverage_info(
        added_lines=added_lines, coverage=make_coverage_obj(**update_obj)
    )
    assert result == expected


def test_get_added_lines(git):
    diff = (
        """+++ b/README.md\n@@ -1,2 +1,3 @@\n-# coverage-comment\n+coverage-comment\n"""
    )
    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=diff)
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
    diff = """diff --git a/action.yml b/action.yml
deleted file mode 100644
index 42249d1..0000000
--- a/action.yml
+++ /dev/null
@@ -1,2 +0,0 @@
-name: Python Coverage Comment
-branding:
diff --git a/README.md b/README.md
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
--- a/bar.txt
+++ b/bar.txt
@@ -8 +7,0 @@
-foo
diff --git a/coverage_comment/annotations.py b/coverage_comment/annotations2.py
similarity index 100%
rename from coverage_comment/annotations.py
rename to coverage_comment/annotations2.py
"""
    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=diff)
    assert coverage.parse_diff_output(diff=diff) == {
        pathlib.Path("README.md"): [1, 3, 4, 5, 6],
        pathlib.Path("foo.txt"): [1],
    }


def test_parse_diff_output__error(git):
    diff = """
@@ -0,0 +1,1 @@
+name: Python Coverage Comment
diff --git a/README.md b/README.md
index 1f1d9a4..e69de29 100644
"""
    git.register("git fetch origin main --depth=1000")()
    git.register("git diff --unified=0 FETCH_HEAD...HEAD")(stdout=diff)
    with pytest.raises(ValueError):
        coverage.parse_diff_output(diff=diff)
