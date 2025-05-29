from __future__ import annotations

import dataclasses
import decimal
import functools
import hashlib
import itertools
import pathlib
from collections.abc import Callable
from importlib import resources

import jinja2
from jinja2.sandbox import SandboxedEnvironment

from coverage_comment import badge, diff_grouper
from coverage_comment import coverage as coverage_module

MARKER = (
    """<!-- This comment was produced by python-coverage-comment-action{id_part} -->"""
)


def uptodate():
    return True


class CommentLoader(jinja2.BaseLoader):
    def __init__(
        self, base_template: str, custom_template: str | None, debug: bool = False
    ):
        self.base_template = base_template
        self.custom_template = custom_template

    def get_source(
        self, environment: jinja2.Environment, template: str
    ) -> tuple[str, str | None, Callable[..., bool]]:
        if template == "base":
            return (
                self.base_template,
                "coverage_comment/template_files/comment.md.j2",
                uptodate,
            )

        if self.custom_template and template == "custom":
            return self.custom_template, None, uptodate

        raise jinja2.TemplateNotFound(template)


class MissingMarker(Exception):
    pass


class TemplateError(Exception):
    pass


def get_marker(marker_id: str | None):
    return MARKER.format(id_part=f" (id: {marker_id})" if marker_id else "")


def pluralize(number, singular="", plural="s"):
    if number == 1:
        return singular
    else:
        return plural


def sign(val: int | decimal.Decimal) -> str:
    return "+" if val > 0 else "" if val < 0 else "±"


def delta(val: int) -> str:
    return f"({sign(val)}{val})"


def compact(val: int) -> str:
    if val < 1_000:
        return str(val)
    if val < 10_000:
        return f"{val / 1_000:.1f}k"
    if val < 1_000_000:
        return f"{val / 1_000:.0f}k"
    return f"{val / 1_000_000:.0f}M"


def remove_exponent(val: decimal.Decimal) -> decimal.Decimal:
    # From https://docs.python.org/3/library/decimal.html#decimal-faq
    return (
        val.quantize(decimal.Decimal(1))
        if val == val.to_integral()
        else val.normalize()
    )


def percentage_value(val: decimal.Decimal, precision: int = 2) -> decimal.Decimal:
    return remove_exponent(
        (decimal.Decimal("100") * val).quantize(
            decimal.Decimal("1." + ("0" * precision)),
            rounding=decimal.ROUND_DOWN,
        )
    )


def pct(val: decimal.Decimal, precision: int = 2) -> str:
    rounded = percentage_value(val=val, precision=precision)
    return f"{rounded:f}%"


def x100(val: decimal.Decimal):
    return val * 100


@dataclasses.dataclass
class FileInfo:
    path: pathlib.Path
    coverage: coverage_module.FileCoverage
    diff: coverage_module.FileDiffCoverage | None
    previous: coverage_module.FileCoverage | None


def get_comment_markdown(
    *,
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
    previous_coverage_rate: decimal.Decimal | None,
    previous_coverage: coverage_module.Coverage | None,
    files: list[FileInfo],
    max_files: int | None,
    count_files: int,
    minimum_green: decimal.Decimal,
    minimum_orange: decimal.Decimal,
    github_host: str,
    repo_name: str,
    pr_number: int,
    base_template: str,
    marker: str,
    subproject_id: str | None = None,
    custom_template: str | None = None,
    pr_targets_default_branch: bool = True,
):
    loader = CommentLoader(base_template=base_template, custom_template=custom_template)
    env = SandboxedEnvironment(loader=loader)
    env.filters["pct"] = pct
    env.filters["delta"] = delta
    env.filters["x100"] = x100
    env.filters["get_evolution_color"] = badge.get_evolution_badge_color
    env.filters["generate_badge"] = badge.get_static_badge_url
    env.filters["pluralize"] = pluralize
    env.filters["compact"] = compact
    env.filters["file_url"] = functools.partial(
        get_file_url, github_host=github_host, repo_name=repo_name, pr_number=pr_number
    )
    env.filters["get_badge_color"] = functools.partial(
        badge.get_badge_color,
        minimum_green=minimum_green,
        minimum_orange=minimum_orange,
    )

    missing_diff_lines = {
        key: list(value)
        for key, value in itertools.groupby(
            diff_grouper.get_diff_missing_groups(
                coverage=coverage, diff_coverage=diff_coverage
            ),
            lambda x: x.file,
        )
    }
    try:
        comment = env.get_template("custom" if custom_template else "base").render(
            previous_coverage_rate=previous_coverage_rate,
            coverage=coverage,
            diff_coverage=diff_coverage,
            previous_coverage=previous_coverage,
            count_files=count_files,
            max_files=max_files,
            files=files,
            missing_diff_lines=missing_diff_lines,
            subproject_id=subproject_id,
            marker=marker,
            pr_targets_default_branch=pr_targets_default_branch,
        )
    except jinja2.exceptions.TemplateError as exc:
        raise TemplateError from exc

    if marker not in comment:
        raise MissingMarker()

    return comment


def select_files(
    *,
    coverage: coverage_module.Coverage,
    diff_coverage: coverage_module.DiffCoverage,
    previous_coverage: coverage_module.Coverage | None = None,
    max_files: int | None,
) -> tuple[list[FileInfo], int]:
    """
    Selects the MAX_FILES files with the most new missing lines sorted by path

    """
    previous_coverage_files = previous_coverage.files if previous_coverage else {}

    files = []
    for path, coverage_file in coverage.files.items():
        diff_coverage_file = diff_coverage.files.get(path)
        previous_coverage_file = previous_coverage_files.get(path)

        file_info = FileInfo(
            path=path,
            coverage=coverage_file,
            diff=diff_coverage_file,
            previous=previous_coverage_file,
        )
        has_diff = bool(diff_coverage_file and diff_coverage_file.added_statements)
        has_evolution_from_previous = (
            previous_coverage_file.info != coverage_file.info
            if previous_coverage_file
            else False
        )

        if has_diff or has_evolution_from_previous:
            files.append(file_info)

    count_files = len(files)
    files = sorted(files, key=sort_order, reverse=True)
    if max_files is not None:
        files = files[:max_files]
    return sorted(files, key=lambda x: x.path), count_files


def sort_order(file_info: FileInfo) -> tuple[int, int, int]:
    """
    Sort order for files:
    1. Files with the most new missing lines
    2. Files with the most added lines (from the diff)
    3. Files with the most new executed lines (including not in the diff)
    """
    new_missing_lines = len(file_info.coverage.missing_lines)
    if file_info.previous:
        new_missing_lines -= len(file_info.previous.missing_lines)

    added_statements = len(file_info.diff.added_statements) if file_info.diff else 0
    new_covered_lines = len(file_info.coverage.executed_lines)
    if file_info.previous:
        new_covered_lines -= len(file_info.previous.executed_lines)

    return abs(new_missing_lines), added_statements, abs(new_covered_lines)


def get_readme_markdown(
    is_public: bool,
    readme_url: str,
    markdown_report: str,
    direct_image_url: str,
    html_report_url: str | None,
    dynamic_image_url: str | None,
    endpoint_image_url: str | None,
    subproject_id: str | None = None,
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
        subproject_id=subproject_id,
    )


def get_log_message(
    is_public: bool,
    readme_url: str,
    direct_image_url: str,
    html_report_url: str | None,
    dynamic_image_url: str | None,
    endpoint_image_url: str | None,
    subproject_id: str | None = None,
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
        subproject_id=subproject_id,
    )


def read_template_file(template: str) -> str:
    return (
        resources.files("coverage_comment") / "template_files" / template
    ).read_text()


def get_file_url(
    filename: pathlib.Path,
    lines: tuple[int, int] | None = None,
    *,
    github_host: str,
    repo_name: str,
    pr_number: int,
) -> str:
    # To link to a file in a PR, GitHub uses the link to the file overview combined with a SHA256 hash of the file path
    s = f"{github_host}/{repo_name}/pull/{pr_number}/files#diff-{hashlib.sha256(str(filename).encode('utf-8')).hexdigest()}"

    if lines is not None:
        # R stands for Right side of the diff. But since we generate these links for new code we only need the right side.
        s += f"R{lines[0]}-R{lines[1]}"

    return s
