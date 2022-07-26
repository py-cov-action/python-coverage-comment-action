import datetime
import functools
import io
import os
import zipfile

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
            "GITHUB_REPOSITORY": "ewjoachim/foobar",
            # Action settings
            "MERGE_COVERAGE_FILES": True,
            "VERBOSE": False,
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
def pull_request_config(base_config):
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


@pytest.fixture
def session():
    """
    You get a session object. Register responses on it:
        session.register(method="GET", path="/a/b")(status_code=200)
    or
        session.register(method="GET", path="/a/b", json=checker)(status_code=200)
    (where checker is a function receiving the json value, and returning True if it
    matches)

    if session.request(method="GET", path="/a/b") is called, it will return a response
    with status_code 200. Also, if not called by the end of the test, it will raise.
    """

    class Session:
        responses = []  # List[Tuples[request kwargs, response kwargs]]

        def request(self, method, path, **kwargs):
            request_kwargs = {"method": method, "path": path} | kwargs

            for i, (match_kwargs, response_kwargs) in enumerate(self.responses):
                match = True
                for key, match_value in match_kwargs.items():
                    if key not in request_kwargs:
                        match = False
                        break
                    request_value = request_kwargs[key]

                    if hasattr(match_value, "__call__"):
                        try:
                            assert match_value(request_value)
                        except Exception:
                            match = False
                            break
                    else:
                        if not match_value == request_value:
                            match = False
                            break
                if match:
                    self.responses.pop(i)
                    return httpx.Response(
                        **response_kwargs,
                        request=httpx.Request(method=method, url=path),
                    )
            assert (
                False
            ), f"No response found for kwargs {request_kwargs}\nExpected answers are {self.responses}"

        def __getattr__(self, value):
            if value in ["get", "post", "patch", "delete", "put"]:
                return functools.partial(self.request, value.upper())
            raise AttributeError(value)

        def register(self, method, path, **request_kwargs):
            request_kwargs = {"method": method, "path": path} | request_kwargs

            def _(**response_kwargs):
                response_kwargs.setdefault("status_code", 200)
                self.responses.append((request_kwargs, response_kwargs))

            return _

    session = Session()
    yield session
    assert not session.responses


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
def git():
    """
    You get a git object. Register calls on it:
        git.register("git checkout master")(exit_code=1)
    or
        session.register("git commit", env={"A": "B"})(stdout="Changed branch")

    If the command was not received by the end of the test, it will raise.
    """

    class Git:
        expected_calls = []

        def command(self, command, *args, env=None):
            args = " ".join(("git", command, *args))
            if not self.expected_calls:
                assert (
                    False
                ), f"Received command `{args}` with env {env} while expecting nothing."

            call = self.expected_calls[0]
            exp_args, exp_env, exit_code, stdout = call
            if not (args == exp_args and exp_env == env):
                assert (
                    False
                ), f"Expected command is not `{args}` with env {env}\nExpected command is {self.expected_calls[0]}"

            self.expected_calls.pop(0)
            if exit_code == 0:
                return stdout
            raise subprocess.GitError

        def __getattr__(self, value):
            return functools.partial(self.command, value.replace("_", "-"))

        def register(self, command, env=None):
            def _(*, exit_code=0, stdout=""):
                self.expected_calls.append((command, env, exit_code, stdout))

            return _

    git = Git()
    yield git
    assert not git.expected_calls
