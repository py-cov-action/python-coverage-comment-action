"""
This module is responsible for identifying what the action should be doing
based on the github event type and repository.

The code in main should be as straightforward as possible, we're offloading
the branching logic to this module.
"""

from __future__ import annotations

from enum import Enum


class Activity(Enum):
    PROCESS_PR = "process_pr"
    POST_COMMENT = "post_comment"
    SAVE_COVERAGE_DATA_FILES = "save_coverage_data_files"


class ActivityNotFound(Exception):
    pass


class ActivityConfigError(Exception):
    pass


def validate_activity(activity: str) -> Activity:
    if activity not in [a.value for a in Activity]:
        raise ActivityConfigError(f"Invalid activity: {activity}")
    return Activity(activity)


def find_activity(
    event_name: str,
    is_default_branch: bool,
    event_type: str | None,
    is_pr_merged: bool,
) -> Activity:
    """Find the activity to perform based on the event type and payload."""
    if event_name == "workflow_run":
        return Activity.POST_COMMENT

    if (
        (event_name == "push" and is_default_branch)
        or event_name == "schedule"
        or (event_name == "pull_request" and event_type == "closed")
        or event_name == "merge_group"
    ):
        if event_name == "pull_request" and event_type == "closed" and not is_pr_merged:
            raise ActivityNotFound
        return Activity.SAVE_COVERAGE_DATA_FILES

    if event_name not in {"pull_request", "push", "merge_group"}:
        raise ActivityNotFound

    return Activity.PROCESS_PR
