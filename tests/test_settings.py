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
            "BADGE_FILENAME": "bar",
            "COMMENT_ARTIFACT_NAME": "baz",
            "COMMENT_FILENAME": "qux",
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
        BADGE_FILENAME=pathlib.Path("bar"),
        COMMENT_ARTIFACT_NAME="baz",
        COMMENT_FILENAME=pathlib.Path("qux"),
        MINIMUM_GREEN=90.0,
        MINIMUM_ORANGE=50.8,
        MERGE_COVERAGE_FILES=True,
        VERBOSE=False,
    )


def test_config__from_environ__error():
    with pytest.raises(ValueError):
        settings.Config.from_environ({"COMMENT_FILENAME": "/a"})
