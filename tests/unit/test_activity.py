from __future__ import annotations

import pytest

from coverage_comment import activity


@pytest.mark.parametrize(
    "event_name, event_action, is_default_branch, expected_activity",
    [
        ("workflow_run", None, True, "post_comment"),
        ("push", None, True, "save_coverage_data_files"),
        ("push", None, False, "process_pr"),
        ("pull_request", "merged", True, "save_coverage_data_files"),
        ("pull_request", None, True, "process_pr"),
        ("pull_request", None, False, "process_pr"),
        ("schedule", None, False, "save_coverage_data_files"),
    ],
)
def test_find_activity(event_name, event_action, is_default_branch, expected_activity):
    result = activity.find_activity(
        event_name=event_name, event_action=event_action, is_default_branch=is_default_branch
    )
    assert result == expected_activity


def test_find_activity_not_found():
    with pytest.raises(activity.ActivityNotFound):
        activity.find_activity(event_name="not_found", is_default_branch=False)
