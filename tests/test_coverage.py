import json
import os

import pytest

from coverage_comment import coverage, subprocess


@pytest.fixture
def in_tmp_path(tmp_path):
    curdir = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(curdir)


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


def test_get_coverage_info__error_base(mocker, caplog):
    caplog.set_level("ERROR")
    mocker.patch(
        "coverage_comment.subprocess.run", side_effect=subprocess.SubProcessError
    )

    with pytest.raises(subprocess.SubProcessError):
        coverage.get_coverage_info(merge=False)

    assert caplog.messages == []


def test_get_coverage_info__error_no_source(mocker, caplog):
    caplog.set_level("ERROR")
    mocker.patch(
        "coverage_comment.subprocess.run",
        side_effect=subprocess.SubProcessError("No source for code: bla"),
    )

    with pytest.raises(subprocess.SubProcessError):
        coverage.get_coverage_info(merge=False)

    assert caplog.messages[0].startswith("Cannot read")
