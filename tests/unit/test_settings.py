from __future__ import annotations

import decimal
import pathlib

import pytest

from coverage_comment import settings


@pytest.mark.parametrize("path", ["a", "a/b/.."])
def test_path_below__ok(path):
    assert settings.path_below(path) == pathlib.Path("a")


@pytest.mark.parametrize("path", ["/a", "a/../.."])
def test_path_below__error(path):
    with pytest.raises(ValueError):
        settings.path_below(path)


def test_config__from_environ__missing():
    with pytest.raises(settings.MissingEnvironmentVariable):
        settings.Config.from_environ({})


def test_config__from_environ__ok():
    assert settings.Config.from_environ(
        {
            "GITHUB_BASE_REF": "master",
            "GITHUB_TOKEN": "foo",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_REF": "master",
            "GITHUB_OUTPUT": "foo.txt",
            "GITHUB_EVENT_NAME": "pull",
            "GITHUB_EVENT_PATH": pathlib.Path("test_event_path"),
            "GITHUB_PR_RUN_ID": "123",
            "GITHUB_STEP_SUMMARY": "step_summary",
            "COMMENT_ARTIFACT_NAME": "baz",
            "COMMENT_FILENAME": "qux",
            "SUBPROJECT_ID": "subproject",
            "COMMENT_TEMPLATE": "footemplate",
            "COVERAGE_DATA_BRANCH": "branchname",
            "COVERAGE_PATH": "source_folder/",
            "MINIMUM_GREEN": "90",
            "MINIMUM_ORANGE": "50.8",
            "MERGE_COVERAGE_FILES": "true",
            "ANNOTATE_MISSING_LINES": "false",
            "ANNOTATION_TYPE": "error",
            "VERBOSE": "false",
            "FORCE_WORKFLOW_RUN": "false",
        }
    ) == settings.Config(
        GITHUB_BASE_REF="master",
        GITHUB_TOKEN="foo",
        GITHUB_REPOSITORY="owner/repo",
        GITHUB_REF="master",
        GITHUB_OUTPUT=pathlib.Path("foo.txt"),
        GITHUB_EVENT_NAME="pull",
        GITHUB_EVENT_PATH=pathlib.Path("test_event_path"),
        GITHUB_PR_RUN_ID=123,
        GITHUB_STEP_SUMMARY=pathlib.Path("step_summary"),
        COMMENT_ARTIFACT_NAME="baz",
        COMMENT_FILENAME=pathlib.Path("qux"),
        SUBPROJECT_ID="subproject",
        COMMENT_TEMPLATE="footemplate",
        COVERAGE_DATA_BRANCH="branchname",
        COVERAGE_PATH=pathlib.Path("source_folder/"),
        MINIMUM_GREEN=decimal.Decimal("90"),
        MINIMUM_ORANGE=decimal.Decimal("50.8"),
        MERGE_COVERAGE_FILES=True,
        ANNOTATE_MISSING_LINES=False,
        ANNOTATION_TYPE="error",
        VERBOSE=False,
        FORCE_WORKFLOW_RUN=False,
    )


def test_config__verbose_deprecated(get_logs):
    assert settings.Config.from_environ(
        {
            "GITHUB_BASE_REF": "master",
            "GITHUB_TOKEN": "foo",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_REF": "master",
            "GITHUB_EVENT_NAME": "pull",
            "GITHUB_EVENT_PATH": pathlib.Path("test_event_path"),
            "GITHUB_PR_RUN_ID": "123",
            "GITHUB_STEP_SUMMARY": "step_summary",
            "VERBOSE": "true",
        }
    ) == settings.Config(
        GITHUB_BASE_REF="master",
        GITHUB_TOKEN="foo",
        GITHUB_REPOSITORY="owner/repo",
        GITHUB_REF="master",
        GITHUB_EVENT_NAME="pull",
        GITHUB_EVENT_PATH=pathlib.Path("test_event_path"),
        GITHUB_PR_RUN_ID=123,
        GITHUB_STEP_SUMMARY=pathlib.Path("step_summary"),
        VERBOSE=False,
    )
    assert get_logs("INFO", "VERBOSE setting is deprecated")


@pytest.fixture
def config():
    defaults = {
        "GITHUB_BASE_REF": "master",
        "GITHUB_TOKEN": "foo",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_REF": "master",
        "GITHUB_EVENT_NAME": "pull",
        "GITHUB_EVENT_PATH": pathlib.Path("test_event_path"),
        "GITHUB_PR_RUN_ID": 123,
        "GITHUB_STEP_SUMMARY": pathlib.Path("step_summary"),
        "COMMENT_ARTIFACT_NAME": "baz",
        "COMMENT_FILENAME": pathlib.Path("qux"),
        "COVERAGE_DATA_BRANCH": "branchname",
        "MINIMUM_GREEN": decimal.Decimal("90"),
        "MINIMUM_ORANGE": decimal.Decimal("50.8"),
        "MERGE_COVERAGE_FILES": True,
    }

    def _(**kwargs):
        return settings.Config(**(defaults | kwargs))

    return _


@pytest.mark.parametrize(
    "github_ref, github_pr_number",
    [
        ("foo", None),
        ("refs/heads/branch-with-pull", None),
        ("refs/tags/tag-with-pull", None),
        ("refs/pull/2/merge", 2),
    ],
)
def test_config__GITHUB_PR_NUMBER(config, github_ref, github_pr_number):
    assert config(GITHUB_REF=github_ref).GITHUB_PR_NUMBER == github_pr_number


@pytest.mark.parametrize(
    "github_ref, github_branch_name",
    [
        ("refs/pull/2/merge", None),
        ("refs/pull/2/head", None),
        ("refs/tags/tag-with-heads", None),
        ("refs/heads/a/b", "a/b"),
    ],
)
def test_config__GITHUB_BRANCH_NAME(config, github_ref, github_branch_name):
    assert config(GITHUB_REF=github_ref).GITHUB_BRANCH_NAME == github_branch_name


def test_config__from_environ__error():
    with pytest.raises(ValueError):
        settings.Config.from_environ({"COMMENT_FILENAME": "/a"})


def test_config__invalid_annotation_type():
    with pytest.raises(settings.InvalidAnnotationType):
        settings.Config.from_environ({"ANNOTATION_TYPE": "foo"})


@pytest.mark.parametrize(
    "input, output",
    [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("foo", False),
    ],
)
def test_str_to_bool(input, output):
    assert settings.str_to_bool(input) is output


def test_final_comment_filename(config):
    config_obj = config(
        COMMENT_FILENAME=pathlib.Path("foo.txt"),
        SUBPROJECT_ID="bar",
    )
    assert config_obj.FINAL_COMMENT_FILENAME == pathlib.Path("foo-bar.txt")


def test_final_coverage_data_branch(config):
    config_obj = config(
        COVERAGE_DATA_BRANCH="foo",
        SUBPROJECT_ID="bar",
    )
    assert config_obj.FINAL_COVERAGE_DATA_BRANCH == "foo-bar"
