from __future__ import annotations

import datetime
import decimal
import io
import os
import pathlib
import shlex
import zipfile
from collections.abc import Callable

import httpx
import pytest

from coverage_comment import coverage as coverage_module
from coverage_comment import github_client, settings, subprocess


@pytest.fixture
def base_config():
    def _(**kwargs):
        defaults = {
            # GitHub stuff
            "GITHUB_TOKEN": "foo",
            "GITHUB_PR_RUN_ID": 123,
            "GITHUB_REPOSITORY": "py-cov-action/foobar",
            "GITHUB_STEP_SUMMARY": pathlib.Path("step_summary"),
            # Action settings
            "MERGE_COVERAGE_FILES": True,
        }
        return settings.Config(**(defaults | kwargs))

    return _


@pytest.fixture
def push_config(base_config):
    def _(**kwargs):
        defaults = {
            # GitHub stuff
            "GITHUB_BASE_REF": "",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "push",
        }
        return base_config(**(defaults | kwargs))

    return _


@pytest.fixture
def pull_request_config(base_config) -> Callable[..., settings.Config]:
    def _(**kwargs):
        defaults = {
            # GitHub stuff
            "GITHUB_BASE_REF": "main",
            "GITHUB_REF": "refs/pull/2/merge",
            "GITHUB_EVENT_NAME": "pull_request",
        }
        return base_config(**(defaults | kwargs))

    return _


@pytest.fixture
def workflow_run_config(base_config):
    def _(**kwargs):
        defaults = {
            # GitHub stuff
            "GITHUB_BASE_REF": "",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_run",
        }
        return base_config(**(defaults | kwargs))

    return _


@pytest.fixture
def session(httpx_mock):
    class FakeSession(httpx.Client):
        def __init__(self):
            super().__init__(base_url="https://example.com")

        def _kwargs(self, method: str, url: str, **kwargs):
            if not url.startswith("https://"):
                url = f"https://example.com/{url.lstrip('/')}"
            return {"method": method, "url": url, **kwargs}

        def get_request(self, *args, **kwargs):
            return httpx_mock.get_request(**self._kwargs(*args, **kwargs))

        def register(self, *args, callback=None, **kwargs):
            if callback:
                return httpx_mock.add_callback(
                    callback, **self._kwargs(*args, **kwargs)
                )
            return httpx_mock.add_response(**self._kwargs(*args, **kwargs))

    return FakeSession()


@pytest.fixture
def gh(session):
    return github_client.GitHub(session=session)


@pytest.fixture
def get_logs(caplog):
    caplog.set_level("DEBUG")

    def _(level=None, match=None):
        return [
            log.message
            for log in caplog.records
            if (level is None or level == log.levelname)
            and (match is None or match in log.message)
        ]

    return _


@pytest.fixture
def in_tmp_path(tmp_path):
    curdir = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(curdir)


@pytest.fixture
def zip_bytes():
    def _(filename, content):
        file = io.BytesIO()
        with zipfile.ZipFile(file, mode="w") as zipf:
            with zipf.open(filename, "w") as subfile:
                subfile.write(content.encode("utf-8"))
        zip_bytes = file.getvalue()
        assert zip_bytes.startswith(b"PK")
        return zip_bytes

    return _


@pytest.fixture
def git(fake_process):
    class FakeGit(subprocess.Git):
        def register(self, cmd: str, **kwargs):
            return fake_process.register(["git", *shlex.split(cmd)], **kwargs)

    return FakeGit()


@pytest.fixture
def output_file(tmp_path):
    file = tmp_path / "temp_output.txt"
    file.touch()

    return file


@pytest.fixture
def summary_file(tmp_path):
    file = tmp_path / "step_summary.txt"
    file.touch()

    return file


@pytest.fixture
def pull_request_event_payload(tmp_path):
    file = tmp_path / "event.json"
    file.touch()

    return file


_is_failed = []


def pytest_runtest_logreport(report):
    if report.outcome == "failed":
        _is_failed.append(True)


@pytest.fixture
def is_failed():
    _is_failed.clear()

    def f():
        return bool(_is_failed)

    yield f
    _is_failed.clear()


@pytest.fixture
def make_coverage():
    def _(code: str, has_branches: bool = True) -> coverage_module.Coverage:
        current_file = None
        coverage_obj = coverage_module.Coverage(
            meta=coverage_module.CoverageMetadata(
                version="1.2.3",
                timestamp=datetime.datetime(2000, 1, 1),
                branch_coverage=True,
                show_contexts=False,
            ),
            info=coverage_module.CoverageInfo(
                covered_lines=0,
                num_statements=0,
                percent_covered=decimal.Decimal("1.0"),
                missing_lines=0,
                excluded_lines=0,
                num_branches=0,
                num_partial_branches=0,
                covered_branches=0,
                missing_branches=0,
            ),
            files={},
        )
        line_number = 0
        # (we start at 0 because the first line will be empty for readabilty)
        for line in code.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("# file: "):
                current_file = pathlib.Path(line.split("# file: ")[1])
                line_number = 0
                continue
            assert current_file, (line, current_file, code)
            line_number += 1
            if coverage_obj.files.get(current_file) is None:
                coverage_obj.files[current_file] = coverage_module.FileCoverage(
                    path=current_file,
                    executed_lines=[],
                    missing_lines=[],
                    excluded_lines=[],
                    info=coverage_module.CoverageInfo(
                        covered_lines=0,
                        num_statements=0,
                        percent_covered=decimal.Decimal("1.0"),
                        missing_lines=0,
                        excluded_lines=0,
                        num_branches=0,
                        num_partial_branches=0,
                        covered_branches=0,
                        missing_branches=0,
                    ),
                )
            if set(line.split()) & {
                "covered",
                "missing",
                "excluded",
                "partial",
                "branch",
            }:
                coverage_obj.files[current_file].info.num_statements += 1
                coverage_obj.info.num_statements += 1
            if "covered" in line or "partial" in line:
                coverage_obj.files[current_file].executed_lines.append(line_number)
                coverage_obj.files[current_file].info.covered_lines += 1
                coverage_obj.info.covered_lines += 1
            elif "missing" in line:
                coverage_obj.files[current_file].missing_lines.append(line_number)
                coverage_obj.files[current_file].info.missing_lines += 1
                coverage_obj.info.missing_lines += 1
            elif "excluded" in line:
                coverage_obj.files[current_file].excluded_lines.append(line_number)
                coverage_obj.files[current_file].info.excluded_lines += 1
                coverage_obj.info.excluded_lines += 1
            if has_branches and "branch" in line:
                coverage_obj.files[current_file].info.num_branches += 1
                coverage_obj.info.num_branches += 1
                if "branch partial" in line:
                    coverage_obj.files[current_file].info.num_partial_branches += 1
                    coverage_obj.info.num_partial_branches += 1
                elif "branch covered" in line:
                    coverage_obj.files[current_file].info.covered_branches += 1
                    coverage_obj.info.covered_branches += 1
                elif "branch missing" in line:
                    coverage_obj.files[current_file].info.missing_branches += 1
                    coverage_obj.info.missing_branches += 1
            info = coverage_obj.files[current_file].info
            coverage_obj.files[
                current_file
            ].info.percent_covered = coverage_module.compute_coverage(
                num_covered=info.covered_lines,
                num_total=info.num_statements,
                num_branches_covered=info.covered_branches,
                num_branches_total=info.num_branches,
            )
            info = coverage_obj.info
            coverage_obj.info.percent_covered = coverage_module.compute_coverage(
                num_covered=info.covered_lines,
                num_total=info.num_statements,
                num_branches_covered=info.covered_branches,
                num_branches_total=info.num_branches,
            )
        return coverage_obj

    return _


@pytest.fixture
def make_diff_coverage():
    return coverage_module.get_diff_coverage_info


@pytest.fixture
def make_coverage_and_diff(make_coverage, make_diff_coverage):
    def _(code: str) -> tuple[coverage_module.Coverage, coverage_module.DiffCoverage]:
        added_lines: dict[pathlib.Path, list[int]] = {}
        new_code = ""
        current_file = None
        # (we start at 0 because the first line will be empty for readabilty)
        line_number = 0
        for line in code.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("# file: "):
                new_code += line + "\n"
                current_file = pathlib.Path(line.split("# file: ")[1])
                line_number = 0
                continue
            assert current_file
            line_number += 1

            if line.startswith("+ "):
                added_lines.setdefault(current_file, []).append(line_number)
                new_code += line[2:] + "\n"
            else:
                new_code += line + "\n"

        coverage = make_coverage("\n" + new_code)
        return coverage, make_diff_coverage(added_lines=added_lines, coverage=coverage)

    return _


@pytest.fixture
def coverage_code():
    return """
        # file: codebase/code.py
        1 covered
        2 covered
        3 covered
        4
        5 branch partial
        6 missing
        7
        8 missing
        9
        10 branch missing
        11 missing
        12 covered
        13 branch covered
        14 covered
        15 branch partial
        16 branch covered
        17 branch missing
        18 covered
        19 covered
        20 branch partial
        21 branch missing
        22 branch covered
        23 branch covered
        24 branch covered
        """


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
                "executed_lines": [
                    1,
                    2,
                    3,
                    5,
                    12,
                    13,
                    14,
                    15,
                    16,
                    18,
                    19,
                    20,
                    22,
                    23,
                    24,
                ],
                "summary": {
                    "covered_lines": 15,
                    "num_statements": 21,
                    "percent_covered": 0.625,
                    "missing_lines": 6,
                    "excluded_lines": 0,
                    "num_branches": 11,
                    "num_partial_branches": 3,
                    "covered_branches": 5,
                    "missing_branches": 3,
                },
                "missing_lines": [6, 8, 10, 11, 17, 21],
                "excluded_lines": [],
            }
        },
        "totals": {
            "covered_lines": 15,
            "num_statements": 21,
            "percent_covered": 0.625,
            "missing_lines": 6,
            "excluded_lines": 0,
            "num_branches": 11,
            "num_partial_branches": 3,
            "covered_branches": 5,
            "missing_branches": 3,
        },
    }


@pytest.fixture
def coverage_obj(make_coverage, coverage_code):
    return make_coverage(coverage_code)


@pytest.fixture
def coverage_obj_no_branch_code():
    return """
        # file: codebase/code.py
        covered
        covered
        missing

        covered
        missing

        missing
        missing
        covered
        """


@pytest.fixture
def coverage_obj_no_branch(make_coverage, coverage_obj_no_branch_code):
    return make_coverage(coverage_obj_no_branch_code, has_branches=False)


@pytest.fixture
def coverage_obj_more_files(make_coverage):
    return make_coverage(
        """
        # file: codebase/code.py
        covered
        covered
        covered

        branch partial
        missing

        missing

        branch missing
        missing

        branch covered
        covered
        # file: codebase/other.py


        missing
        covered
        missing
        missing

        missing
        covered
        covered
        """
    )


@pytest.fixture
def make_coverage_obj(coverage_obj_more_files):
    def f(**kwargs):
        obj = coverage_obj_more_files
        for key, value in kwargs.items():
            vars(obj.files[pathlib.Path(key)]).update(value)
        return obj

    return f


@pytest.fixture
def diff_coverage_obj(coverage_obj, make_diff_coverage):
    return make_diff_coverage(
        added_lines={pathlib.Path("codebase/code.py"): [3, 4, 5, 6, 7, 8, 9, 12]},
        coverage=coverage_obj,
    )


@pytest.fixture
def diff_coverage_obj_more_files(coverage_obj_more_files, make_diff_coverage):
    return make_diff_coverage(
        added_lines={
            pathlib.Path("codebase/code.py"): [3, 4, 5, 6, 7, 8, 9, 12],
            pathlib.Path("codebase/other.py"): [1, 2, 3, 4, 5, 6, 7, 8, 17],
        },
        coverage=coverage_obj_more_files,
    )
