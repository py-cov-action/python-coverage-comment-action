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
    violations: list[int], separators: set[int]
) -> list[tuple[int, int]]:
    """
    Given a list of violations and a list of separators, return a list of
    ranges (start, included end) describing groups of violations. A group of
    violations is considered contiguous if there are no more than
    MAX_ANNOTATION_GAP lines between each subsequent pair of violations in the
    group, and if none of the lines in the gap are separators.
    """
    contiguous_groups: list[tuple[int, int]] = []
    for _, contiguous_group in itertools.groupby(
        zip(violations, itertools.count(1)), lambda x: x[1] - x[0]
    ):
        grouped_violations = (e[0] for e in contiguous_group)
        first = next(grouped_violations)
        try:
            *_, last = grouped_violations
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

        gap_is_small = next_start - last_end - 1 <= MAX_ANNOTATION_GAP
        gap_contains_separators = set(range(last_end + 1, next_start)) & separators

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

        violations = diff_file.violation_lines
        # Lines that are covered or excluded should not be considered for
        # filling a gap between violation groups.
        # (so, lines that can appear in a gap are lines that are missing, or
        # lines that do not contain code: blank lines or lines containing comments)
        separators = {
            *coverage_file.executed_lines,
            *coverage_file.excluded_lines,
        }

        for start, end in compute_contiguous_groups(
            violations=violations, separators=separators
        ):
            yield Annotation(
                file=path,
                line_start=start,
                line_end=end,
            )
