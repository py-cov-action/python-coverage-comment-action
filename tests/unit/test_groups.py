from __future__ import annotations

import pytest

from coverage_comment import groups


@pytest.mark.parametrize(
    "values, separators, joiners, expected",
    [
        # Single line
        ([1], {1}, set(), [(1, 1)]),
        # Pair of line
        ([1, 2], {1, 2}, set(), [(1, 2)]),
        # Group of lines
        ([1, 2, 3], {1, 2, 3}, set(), [(1, 3)]),
        # Pair of lines with a blank line in between
        ([1, 3], {1, 3}, set(), [(1, 3)]),
        # Pair of lines with a separator in between
        ([1, 3], {1, 2, 3}, set(), [(1, 1), (3, 3)]),
        # 3 groups of lines with separators in between
        ([1, 3, 5], {1, 2, 3, 4, 5}, set(), [(1, 1), (3, 3), (5, 5)]),
        # 3 groups of lines with a small gap & no separator in between
        ([1, 3, 5], {1, 3, 5}, set(), [(1, 5)]),
        # with a 1-sized gap
        ([1, 3], {1, 3}, set(), [(1, 3)]),
        # with a 2-sized gap
        ([1, 4], {1, 4}, set(), [(1, 4)]),
        # with a 3-sized gap
        ([1, 5], {1, 5}, set(), [(1, 5)]),
        # with a 4-sized gap: that's > MAX_ANNOTATION_GAP so we split
        ([1, 6], {1, 6}, set(), [(1, 1), (6, 6)]),
        # with a 5-sized gap but it's all joiners
        ([1, 7], {1, 7}, {2, 3, 4, 5, 6}, [(1, 7)]),
        # same with a separator
        ([1, 7], {1, 4, 7}, {2, 3, 4, 5, 6}, [(1, 7)]),
        # an 8-sized gap with joiners and 2 non-joiners (we merge)
        ([1, 9], {1, 9}, {2, 3, 5, 7, 8}, [(1, 9)]),
        # an 8-sized gap with joiners and 4 non-joiners (we split)
        ([1, 9], {1, 9}, {2, 3, 7}, [(1, 1), (9, 9)]),
        # pair of lines with a gap that is too big, and with a separator in between
        ([1, 6], {1, 3, 6}, set(), [(1, 1), (6, 6)]),
        # single line, then group
        ([1, 2, 3, 5], {1, 2, 3, 5}, set(), [(1, 5)]),
        # group, then single line
        ([1, 3, 4, 5], {1, 3, 4, 5}, set(), [(1, 5)]),
    ],
)
def test_compute_contiguous_groups(values, separators, joiners, expected):
    result = groups.compute_contiguous_groups(
        values=values, separators=separators, joiners=joiners, max_gap=3
    )
    assert result == expected
