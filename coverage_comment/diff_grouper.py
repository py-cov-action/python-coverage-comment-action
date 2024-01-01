from __future__ import annotations

from collections.abc import Iterable

from coverage_comment import coverage as coverage_module
from coverage_comment import groups

MAX_ANNOTATION_GAP = 3


def get_diff_missing_groups(
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
) -> Iterable[groups.Group]:
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

        for start, end in groups.compute_contiguous_groups(
            values=diff_file.missing_statements,
            separators=separators,
            joiners=joiners,
            max_gap=MAX_ANNOTATION_GAP,
        ):
            yield groups.Group(
                file=path,
                line_start=start,
                line_end=end,
            )
