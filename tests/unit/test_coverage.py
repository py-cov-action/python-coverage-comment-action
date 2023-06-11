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

    result = coverage.get_coverage_info(merge=True, coverage_path=".")

    assert run.call_args_list == [
        mocker.call("coverage", "combine", path="."),
        mocker.call("coverage", "json", "-o", "-", path="."),
    ]

    assert result == coverage_obj


def test_get_coverage_info__no_merge(mocker, coverage_json):
    run = mocker.patch(
        "coverage_comment.subprocess.run", return_value=json.dumps(coverage_json)
    )

    coverage.get_coverage_info(merge=False, coverage_path=".")

    assert mocker.call("coverage", "combine", path=".") not in run.call_args_list


def test_get_coverage_info__error_base(mocker, get_logs):
    mocker.patch(
        "coverage_comment.subprocess.run", side_effect=subprocess.SubProcessError
    )

    with pytest.raises(subprocess.SubProcessError):
        coverage.get_coverage_info(merge=False, coverage_path=".")

    assert not get_logs("ERROR")


def test_get_coverage_info__error_no_source(mocker, get_logs):
    mocker.patch(
        "coverage_comment.subprocess.run",
        side_effect=subprocess.SubProcessError("No source for code: bla"),
    )

    with pytest.raises(subprocess.SubProcessError):
        coverage.get_coverage_info(merge=False, coverage_path=".")

    assert get_logs("ERROR", "Cannot read")


def test_generate_coverage_html_files(mocker):
    run = mocker.patch(
        "coverage_comment.subprocess.run",
    )

    coverage.generate_coverage_html_files(
        destination=pathlib.Path("/tmp/foo"), coverage_path="."
    )

    assert run.call_args_list == [
        mocker.call(
            "coverage", "html", "--skip-empty", "--directory", "/tmp/foo", path="."
        ),
    ]


def test_generate_coverage_markdown(mocker):
    run = mocker.patch("coverage_comment.subprocess.run", return_value="foo")

    result = coverage.generate_coverage_markdown(coverage_path=".")

    assert run.call_args_list == [
        mocker.call(
            "coverage", "report", "--format=markdown", "--show-missing", path="."
        ),
    ]

    assert result == "foo"
