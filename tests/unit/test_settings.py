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
            "GITHUB_EVENT_NAME": "pull",
            "GITHUB_PR_RUN_ID": "123",
            "COMMENT_ARTIFACT_NAME": "baz",
            "COMMENT_FILENAME": "qux",
            "COMMENT_TEMPLATE": "footemplate",
            "COVERAGE_DATA_BRANCH": "branchname",
            "MINIMUM_GREEN": "90",
            "MINIMUM_ORANGE": "50.8",
            "MERGE_COVERAGE_FILES": "true",
            "VERBOSE": "false",
        }
    ) == settings.Config(
        GITHUB_BASE_REF="master",
        GITHUB_TOKEN="foo",
        GITHUB_REPOSITORY="owner/repo",
        GITHUB_REF="master",
        GITHUB_EVENT_NAME="pull",
        GITHUB_PR_RUN_ID=123,
        COMMENT_ARTIFACT_NAME="baz",
        COMMENT_FILENAME=pathlib.Path("qux"),
        COMMENT_TEMPLATE="footemplate",
        COVERAGE_DATA_BRANCH="branchname",
        MINIMUM_GREEN=90.0,
        MINIMUM_ORANGE=50.8,
        MERGE_COVERAGE_FILES=True,
        VERBOSE=False,
    )


@pytest.fixture
def config():
    defaults = {
        "GITHUB_BASE_REF": "master",
        "GITHUB_TOKEN": "foo",
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_REF": "master",
        "GITHUB_EVENT_NAME": "pull",
        "GITHUB_PR_RUN_ID": 123,
        "COMMENT_ARTIFACT_NAME": "baz",
        "COMMENT_FILENAME": pathlib.Path("qux"),
        "COVERAGE_DATA_BRANCH": "branchname",
        "MINIMUM_GREEN": 90.0,
        "MINIMUM_ORANGE": 50.8,
        "MERGE_COVERAGE_FILES": True,
        "VERBOSE": False,
    }

    def _(**kwargs):
        return settings.Config(**(defaults | kwargs))

    return _


@pytest.mark.parametrize(
    "github_ref, github_pr_number",
    [
        ("foo", None),
        ("refs/pull/2/merge", 2),
    ],
)
def test_config__GITHUB_PR_NUMBER(config, github_ref, github_pr_number):
    assert config(GITHUB_REF=github_ref).GITHUB_PR_NUMBER == github_pr_number


def test_config__from_environ__error():
    with pytest.raises(ValueError):
        settings.Config.from_environ({"COMMENT_FILENAME": "/a"})


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
