from __future__ import annotations

import pytest

from coverage_comment import activity


@pytest.mark.parametrize(
    "event_name, is_default_branch, event_type, is_pr_merged, expected_activity",
    [
        ("workflow_run", True, None, False, activity.Activity.POST_COMMENT),
        ("push", True, None, False, activity.Activity.SAVE_COVERAGE_DATA_FILES),
        ("push", False, None, False, activity.Activity.PROCESS_PR),
        (
            "pull_request",
            True,
            "closed",
            True,
            activity.Activity.SAVE_COVERAGE_DATA_FILES,
        ),
        ("pull_request", True, None, False, activity.Activity.PROCESS_PR),
        ("pull_request", False, None, False, activity.Activity.PROCESS_PR),
        ("schedule", False, None, False, activity.Activity.SAVE_COVERAGE_DATA_FILES),
        ("merge_group", False, None, False, activity.Activity.SAVE_COVERAGE_DATA_FILES),
    ],
)
def test_find_activity(
    event_name, is_default_branch, event_type, is_pr_merged, expected_activity
):
    result = activity.find_activity(
        event_name=event_name,
        is_default_branch=is_default_branch,
        event_type=event_type,
        is_pr_merged=is_pr_merged,
    )
    assert result == expected_activity


def test_find_activity_not_found():
    with pytest.raises(activity.ActivityNotFound):
        activity.find_activity(
            event_name="not_found",
            is_default_branch=False,
            event_type="not_found",
            is_pr_merged=False,
        )


def test_find_activity_pr_closed_not_merged():
    with pytest.raises(activity.ActivityNotFound):
        activity.find_activity(
            event_name="pull_request",
            is_default_branch=False,
            event_type="closed",
            is_pr_merged=False,
        )


def test_validate_activity__invalid():
    with pytest.raises(activity.ActivityConfigError):
        activity.validate_activity("invalid")


def test_validate_activity__valid():
    result = activity.validate_activity("process_pr")
    assert result == activity.Activity.PROCESS_PR
