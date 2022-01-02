from importlib import resources

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
    env.filters["pct"] = pct

    return env.from_string(template).render(
        previous_coverage_rate=previous_coverage_rate,
        coverage=coverage,
        diff_coverage=diff_coverage,
        marker=MARKER,
    )


def read_template_file() -> str:
    return resources.read_text("coverage_comment", "default.md.j2")


def pct(val):
    return f"{val:.0%}"
