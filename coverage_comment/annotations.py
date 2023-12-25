from __future__ import annotations

import dataclasses
import functools
import itertools
import pathlib
from collections.abc import Iterable

from coverage_comment import coverage as coverage_module

MAX_ANNOTATION_GAP = 3


@dataclasses.dataclass(frozen=True)
class Annotation:
    file: pathlib.Path
    line_start: int
    line_end: int


def compute_contiguous_groups(
    values: list[int], separators: set[int], joiners: set[int]
) -> list[tuple[int, int]]:
    """
    Given a list of (sorted) values, a list of separators and a list of
    joiners, return a list of ranges (start, included end) describing groups of
    values.

    Groups are created by joining contiguous values together, and in some cases
    by merging groups, enclosing a gap of values between them. Gaps that may be
    enclosed are small gaps (<= MAX_ANNOTATION_GAP values after removing all
    joiners) where no line is a "separator"
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

        gap_is_small = len(gap) <= MAX_ANNOTATION_GAP
        gap_contains_separators = gap & separators

        if gap_is_small and not gap_contains_separators:
            acc[-1] = (last_start, next_end)
            return acc

        acc.append(group)
        return acc

    return functools.reduce(reducer, contiguous_groups, [])


def group_annotations(
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
) -> Iterable[Annotation]:
    for path, diff_file in diff_coverage.files.items():
        coverage_file = coverage.files[path]

        # Lines that are covered or excluded should not be considered for
        # filling a gap between violation groups.
        # (so, lines that can appear in a gap are lines that are missing, or
        # lines that do not contain code: blank lines or lines containing comments)
        separators = {
            *coverage_file.executed_lines,
            *coverage_file.excluded_lines,
        }
        # Lines that are added should be considered for filling a gap, unless
        # they are separators.
        joiners = set(diff_file.added_lines) - separators

        for start, end in compute_contiguous_groups(
            values=diff_file.missing_lines,
            separators=separators,
            joiners=joiners,
        ):
            yield Annotation(
                file=path,
                line_start=start,
                line_end=end,
            )
