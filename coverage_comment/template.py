import decimal
from collections.abc import Callable
from importlib import resources

import jinja2
from jinja2.sandbox import SandboxedEnvironment

from coverage_comment import coverage as coverage_module

MARKER = (
    """<!-- This comment was produced by python-coverage-comment-action{id_part} -->"""
)


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


def get_marker(marker_id: str | None):
    return MARKER.format(id_part=f" (id: {marker_id})" if marker_id else "")


def get_comment_markdown(
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
    previous_coverage_rate: decimal.Decimal | None,
    base_template: str,
    marker: str,
    subproject_id: str | None = None,
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
            subproject_id=subproject_id,
            marker=marker,
        )
    except jinja2.exceptions.TemplateError as exc:
        raise TemplateError from exc

    if marker not in comment:
        raise MissingMarker()

    return comment


def get_readme_markdown(
    is_public: bool,
    readme_url: str,
    markdown_report: str,
    direct_image_url: str,
    html_report_url: str | None,
    dynamic_image_url: str | None,
    endpoint_image_url: str | None,
):
    env = SandboxedEnvironment()
    template = jinja2.Template(read_template_file("readme.md.j2"))
    return env.get_template(template).render(
        is_public=is_public,
        readme_url=readme_url,
        markdown_report=markdown_report,
        direct_image_url=direct_image_url,
        html_report_url=html_report_url,
        dynamic_image_url=dynamic_image_url,
        endpoint_image_url=endpoint_image_url,
    )


def get_log_message(
    is_public: bool,
    readme_url: str,
    direct_image_url: str,
    html_report_url: str | None,
    dynamic_image_url: str | None,
    endpoint_image_url: str | None,
):
    env = SandboxedEnvironment()
    template = jinja2.Template(read_template_file("log.txt.j2"))
    return env.get_template(template).render(
        is_public=is_public,
        html_report_url=html_report_url,
        direct_image_url=direct_image_url,
        endpoint_image_url=endpoint_image_url,
        dynamic_image_url=dynamic_image_url,
        readme_url=readme_url,
    )


def read_template_file(template: str) -> str:
    return (
        resources.files("coverage_comment") / "template_files" / template
    ).read_text()


def pct(val: decimal.Decimal | float) -> str:
    if isinstance(val, decimal.Decimal):
        val *= decimal.Decimal("100")
        return f"{val.quantize(decimal.Decimal('0.01'), rounding=decimal.ROUND_DOWN).normalize():f}%"
    else:
        return f"{val:.0%}"
