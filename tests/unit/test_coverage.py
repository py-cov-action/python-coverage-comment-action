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

    result = coverage.get_coverage_info(merge=True)

    assert run.call_args_list == [
        mocker.call("coverage", "combine"),
        mocker.call("coverage", "json", "-o", "-"),
    ]

    assert result == coverage_obj


def test_get_coverage_info__no_merge(mocker, coverage_json):
    run = mocker.patch(
        "coverage_comment.subprocess.run", return_value=json.dumps(coverage_json)
    )

    coverage.get_coverage_info(merge=False)

    assert mocker.call("coverage", "combine") not in run.call_args_list


def test_get_coverage_info__error_base(mocker, get_logs):
    mocker.patch(
        "coverage_comment.subprocess.run", side_effect=subprocess.SubProcessError
    )

    with pytest.raises(subprocess.SubProcessError):
        coverage.get_coverage_info(merge=False)

    assert not get_logs("ERROR")


def test_get_coverage_info__error_no_source(mocker, get_logs):
    mocker.patch(
        "coverage_comment.subprocess.run",
        side_effect=subprocess.SubProcessError("No source for code: bla"),
    )

    with pytest.raises(subprocess.SubProcessError):
        coverage.get_coverage_info(merge=False)

    assert get_logs("ERROR", "Cannot read")


def test_generate_coverage_html_files(mocker):
    run = mocker.patch(
        "coverage_comment.subprocess.run",
    )

    coverage.generate_coverage_html_files(path=pathlib.Path("/tmp/foo"))

    assert run.call_args_list == [
        mocker.call("coverage", "html", "--skip-empty", "--directory", "/tmp/foo"),
    ]


def test_generate_coverage_markdown(mocker):
    run = mocker.patch("coverage_comment.subprocess.run", return_value="foo")

    result = coverage.generate_coverage_markdown()

    assert run.call_args_list == [
        mocker.call("coverage", "report", "--format=markdown", "--show-missing"),
    ]

    assert result == "foo"
