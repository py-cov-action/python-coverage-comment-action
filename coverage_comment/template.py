import pathlib

import jinja2

from coverage_comment import coverage as coverage_module

MARKER = """<!-- This comment was produced by python-coverage-comment-action -->"""


def get_markdown_comment(
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
    previous_coverage_rate: float | None,
    template: str,
):
    env = jinja2.Environment()

    return env.from_string(template).render(
        previous_coverage_rate=previous_coverage_rate,
        coverage=coverage,
        diff_coverage=diff_coverage,
        marker=MARKER,
        pct=pct,
    )


def get_default_template():
    return pathlib.Path("default.md.j2").read_text()


def pct(val):
    return f"{val:.0%}"
