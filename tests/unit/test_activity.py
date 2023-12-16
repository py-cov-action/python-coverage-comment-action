from __future__ import annotations

import pytest

from coverage_comment import activity


@pytest.mark.parametrize(
    "event_name, is_default_branch, expected_activity",
    [
        ("workflow_run", True, "post_comment"),
        ("push", True, "save_coverage_data_files"),
        ("push", False, "process_pr"),
        ("pull_request", True, "process_pr"),
        ("pull_request", False, "process_pr"),
    ],
)
def test_find_activity(event_name, is_default_branch, expected_activity):
    result = activity.find_activity(
        event_name=event_name, is_default_branch=is_default_branch
    )
    assert result == expected_activity


def test_find_activity_not_found():
    with pytest.raises(activity.ActivityNotFound):
        activity.find_activity(event_name="not_found", is_default_branch=False)
