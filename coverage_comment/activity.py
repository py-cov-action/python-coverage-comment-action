"""
This module is responsible for identifying what the action should be doing
based on the github event type and repository.

The code in main should be as straightforward as possible, we're offloading
the branching logic to this module.
"""

from __future__ import annotations


class ActivityNotFound(Exception):
    pass


def find_activity(
    event_name: str,
    is_default_branch: bool,
    event_action: str | None = None,
) -> str:
    """Find the activity to perform based on the event type and payload."""
    if event_name == "workflow_run":
        return "post_comment"

    if (event_name == "push" and is_default_branch) or (event_name == "pull_request" and event_action == "merged" and is_default_branch) or event_name == "schedule":
        return "save_coverage_data_files"

    if event_name not in {"pull_request", "push"}:
        raise ActivityNotFound

    return "process_pr"
