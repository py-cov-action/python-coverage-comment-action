from __future__ import annotations

import pytest

from coverage_comment import activity


@pytest.mark.parametrize(
    "event_name, is_default_branch, event_type, is_pr_merged, expected_activity",
    [
        ("workflow_run", True, None, False, "post_comment"),
        ("push", True, None, False, "save_coverage_data_files"),
        ("push", False, None, False, "process_pr"),
        ("pull_request", True, "closed", True, "save_coverage_data_files"),
        ("pull_request", True, None, False, "process_pr"),
        ("pull_request", False, None, False, "process_pr"),
        ("schedule", False, None, False, "save_coverage_data_files"),
        ("merge_group", False, None, False, "save_coverage_data_files"),
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
