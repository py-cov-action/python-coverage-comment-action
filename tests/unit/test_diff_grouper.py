from __future__ import annotations

import pathlib

from coverage_comment import diff_grouper, groups


def test_group_annotations(coverage_obj, diff_coverage_obj):
    result = diff_grouper.get_diff_missing_groups(
        coverage=coverage_obj, diff_coverage=diff_coverage_obj
    )

    assert list(result) == [
        groups.Group(file=pathlib.Path("codebase/code.py"), line_start=6, line_end=8),
    ]


def test_group_annotations_more_files(
    coverage_obj_more_files, diff_coverage_obj_more_files
):
    result = diff_grouper.get_diff_missing_groups(
        coverage=coverage_obj_more_files,
        diff_coverage=diff_coverage_obj_more_files,
    )

    assert list(result) == [
        groups.Group(file=pathlib.Path("codebase/code.py"), line_start=6, line_end=8),
        groups.Group(
            file=pathlib.Path("codebase/other.py"), line_start=17, line_end=17
        ),
    ]
