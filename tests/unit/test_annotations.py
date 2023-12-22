from __future__ import annotations

import pathlib

import pytest

from coverage_comment import annotations


@pytest.mark.parametrize(
    "violations, separators, expected",
    [
        # Single line
        ([1], {1}, [(1, 1)]),
        # Pair of line
        ([1, 2], {1, 2}, [(1, 2)]),
        # Group of lines
        ([1, 2, 3], {1, 2, 3}, [(1, 3)]),
        # Pair of lines with a blank line in between
        ([1, 3], {1, 3}, [(1, 3)]),
        # Pair of lines with a separator in between
        ([1, 3], {1, 2, 3}, [(1, 1), (3, 3)]),
        # 3 groups of lines with separators in between
        ([1, 3, 5], {1, 2, 3, 4, 5}, [(1, 1), (3, 3), (5, 5)]),
        # 3 groups of lines with a small gap & no separator in between
        ([1, 3, 5], {1, 3, 5}, [(1, 5)]),
        # with a 1-sized gap
        ([1, 3], {1, 3}, [(1, 3)]),
        # with a 2-sized gap
        ([1, 4], {1, 4}, [(1, 4)]),
        # with a 3-sized gap
        ([1, 5], {1, 5}, [(1, 5)]),
        # with a 4-sized gap: that's > MAX_ANNOTATION_GAP so we split
        ([1, 6], {1, 6}, [(1, 1), (6, 6)]),
        # pair of lines with a gap that is too big, and with a separator in between
        ([1, 6], {1, 3, 6}, [(1, 1), (6, 6)]),
        # single line, then group
        ([1, 2, 3, 5], {1, 2, 3, 5}, [(1, 5)]),
        # group, then single line
        ([1, 3, 4, 5], {1, 3, 4, 5}, [(1, 5)]),
    ],
)
def test_compute_contiguous_groups(violations, separators, expected):
    result = annotations.compute_contiguous_groups(violations, separators)
    assert result == expected


def test_group_annotations(coverage_obj, diff_coverage_obj):
    result = annotations.group_annotations(
        coverage=coverage_obj, diff_coverage=diff_coverage_obj
    )

    assert list(result) == [
        annotations.Annotation(
            file=pathlib.Path("codebase/code.py"), line_start=7, line_end=9
        )
    ]
