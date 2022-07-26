from collections.abc import Callable
from importlib import resources

import jinja2
from jinja2.sandbox import SandboxedEnvironment

from coverage_comment import coverage as coverage_module

MARKER = """<!-- This comment was produced by python-coverage-comment-action -->"""


def uptodate():
    return True


class CommentLoader(jinja2.BaseLoader):
    def __init__(self, base_template: str, custom_template: str | None):
        self.base_template = base_template
        self.custom_template = custom_template

    def get_source(
        self, environment: jinja2.Environment, template: str
    ) -> tuple[str, str | None, Callable[..., bool]]:
        if template == "base":
            return self.base_template, None, uptodate

        if self.custom_template and template == "custom":
            return self.custom_template, None, uptodate

        raise jinja2.TemplateNotFound(template)


class MissingMarker(Exception):
    pass


class TemplateError(Exception):
    pass


def get_markdown_comment(
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
    previous_coverage_rate: float | None,
    base_template: str,
    custom_template: str | None = None,
):
    loader = CommentLoader(base_template=base_template, custom_template=custom_template)
    env = SandboxedEnvironment(loader=loader)
    env.filters["pct"] = pct

    try:
        comment = env.get_template("custom" if custom_template else "base").render(
            previous_coverage_rate=previous_coverage_rate,
            coverage=coverage,
            diff_coverage=diff_coverage,
            marker=MARKER,
        )
    except jinja2.exceptions.TemplateError as exc:
        raise TemplateError from exc

    if MARKER not in comment:
        raise MissingMarker()

    return comment


def read_template_file() -> str:
    return resources.read_text("coverage_comment", "default.md.j2")


def pct(val):
    return f"{val:.0%}"
