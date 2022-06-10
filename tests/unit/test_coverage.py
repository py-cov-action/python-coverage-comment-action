import json

import pytest

from coverage_comment import coverage, subprocess


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


def test_get_coverage_info__include_raw(mocker, coverage_json, coverage_obj):
    run = mocker.patch(
        "coverage_comment.subprocess.run", return_value=json.dumps(coverage_json)
    )

    result = coverage.get_coverage_info(merge=True, include_raw_output=True)

    assert run.call_args_list == [
        mocker.call("coverage", "combine"),
        mocker.call("coverage", "json", "-o", "-"),
        mocker.call("coverage", "report"),
    ]
    # TODO: test correctness too


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
