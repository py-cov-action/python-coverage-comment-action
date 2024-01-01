from __future__ import annotations

import dataclasses
import functools
import itertools
import pathlib


@dataclasses.dataclass(frozen=True)
class Group:
    file: pathlib.Path
    line_start: int
    line_end: int


def compute_contiguous_groups(
    values: list[int], separators: set[int], joiners: set[int], max_gap: int
) -> list[tuple[int, int]]:
    """
    Given a list of (sorted) values, a list of separators and a list of
    joiners, return a list of ranges (start, included end) describing groups of
    values.

    Groups are created by joining contiguous values together, and in some cases
    by merging groups, enclosing a gap of values between them. Gaps that may be
    enclosed are small gaps (<= max_gap values after removing all joiners)
    where no line is a "separator"
    """
    contiguous_groups: list[tuple[int, int]] = []
    for _, contiguous_group in itertools.groupby(
        zip(values, itertools.count(1)), lambda x: x[1] - x[0]
    ):
        grouped_values = (e[0] for e in contiguous_group)
        first = next(grouped_values)
        try:
            *_, last = grouped_values
        except ValueError:
            last = first
        contiguous_groups.append((first, last))

    def reducer(
        acc: list[tuple[int, int]], group: tuple[int, int]
    ) -> list[tuple[int, int]]:
        if not acc:
            return [group]

        last_group = acc[-1]
        last_start, last_end = last_group
        next_start, next_end = group

        gap = set(range(last_end + 1, next_start)) - joiners

        gap_is_small = len(gap) <= max_gap
        gap_contains_separators = gap & separators

        if gap_is_small and not gap_contains_separators:
            acc[-1] = (last_start, next_end)
            return acc

        acc.append(group)
        return acc

    return functools.reduce(reducer, contiguous_groups, [])
