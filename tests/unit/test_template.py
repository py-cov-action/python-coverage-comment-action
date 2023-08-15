import datetime
import decimal
import pathlib

import pytest

from coverage_comment import coverage, template


def test_get_comment_markdown(coverage_obj, diff_coverage_obj):
    result = (
        template.get_comment_markdown(
            coverage=coverage_obj,
            diff_coverage=diff_coverage_obj,
            previous_coverage_rate=decimal.Decimal("0.92"),
            marker="<!-- foo -->",
            base_template="""
        {{ previous_coverage_rate | pct }}
        {{ coverage.info.percent_covered | pct }}
        {{ diff_coverage.total_percent_covered | pct }}
        {% block foo %}foo{% endblock foo %}
        {{ marker }}
        """,
            custom_template="""{% extends "base" %}
        {% block foo %}bar{% endblock foo %}
        """,
        )
        .strip()
        .split(maxsplit=4)
    )

    expected = [
        "92%",
        "75%",
        "80%",
        "bar",
        "<!-- foo -->",
    ]

    assert result == expected


def test_template(coverage_obj, diff_coverage_obj):
    result = template.get_comment_markdown(
        coverage=coverage_obj,
        diff_coverage=diff_coverage_obj,
        previous_coverage_rate=decimal.Decimal("0.92"),
        base_template=template.read_template_file("comment.md.j2"),
        marker="<!-- foo -->",
        subproject_id="foo",
        custom_template="""{% extends "base" %}
        {% block emoji_coverage_down %}:sob:{% endblock emoji_coverage_down %}
        """,
    )
    expected = """## Coverage report (foo)
The coverage rate went from `92%` to `75%` :sob:
The branch rate is `50%`.

`80%` of new lines are covered.

<details>
<summary>Diff Coverage details (click to unfold)</summary>

### codebase/code.py
`80%` of new lines are covered (`75%` of the complete file).
Missing lines: `7`, `9`

</details>
<!-- foo -->"""
    assert result == expected


def test_template_full():
    cov = coverage.Coverage(
        meta=coverage.CoverageMetadata(
            version="1.2.3",
            timestamp=datetime.datetime(2000, 1, 1),
            branch_coverage=True,
            show_contexts=False,
        ),
        info=coverage.CoverageInfo(
            covered_lines=6,
            num_statements=6,
            percent_covered=decimal.Decimal("1"),
            missing_lines=0,
            excluded_lines=0,
            num_branches=2,
            num_partial_branches=0,
            covered_branches=2,
            missing_branches=0,
        ),
        files={
            pathlib.Path("codebase/code.py"): coverage.FileCoverage(
                path=pathlib.Path("codebase/code.py"),
                executed_lines=[1, 2, 5, 6, 9],
                missing_lines=[],
                excluded_lines=[],
                info=coverage.CoverageInfo(
                    covered_lines=5,
                    num_statements=6,
                    percent_covered=decimal.Decimal("5") / decimal.Decimal("6"),
                    missing_lines=1,
                    excluded_lines=0,
                    num_branches=2,
                    num_partial_branches=0,
                    covered_branches=2,
                    missing_branches=0,
                ),
            ),
            pathlib.Path("codebase/other.py"): coverage.FileCoverage(
                path=pathlib.Path("codebase/other.py"),
                executed_lines=[1, 2, 3],
                missing_lines=[],
                excluded_lines=[],
                info=coverage.CoverageInfo(
                    covered_lines=6,
                    num_statements=6,
                    percent_covered=decimal.Decimal("1"),
                    missing_lines=0,
                    excluded_lines=0,
                    num_branches=2,
                    num_partial_branches=0,
                    covered_branches=2,
                    missing_branches=0,
                ),
            ),
        },
    )

    diff_cov = coverage.DiffCoverage(
        total_num_lines=6,
        total_num_violations=0,
        total_percent_covered=decimal.Decimal("1"),
        num_changed_lines=39,
        files={
            pathlib.Path("codebase/code.py"): coverage.FileDiffCoverage(
                path=pathlib.Path("codebase/code.py"),
                percent_covered=decimal.Decimal("0.5"),
                violation_lines=[5],
            ),
            pathlib.Path("codebase/other.py"): coverage.FileDiffCoverage(
                path=pathlib.Path("codebase/other.py"),
                percent_covered=decimal.Decimal("1"),
                violation_lines=[],
            ),
        },
    )

    result = template.get_comment_markdown(
        coverage=cov,
        diff_coverage=diff_cov,
        previous_coverage_rate=decimal.Decimal("1.0"),
        marker="<!-- foo -->",
        base_template=template.read_template_file("comment.md.j2"),
    )
    expected = """## Coverage report
The coverage rate went from `100%` to `100%` :arrow_right:
The branch rate is `100%`.

`100%` of new lines are covered.

<details>
<summary>Diff Coverage details (click to unfold)</summary>

### codebase/code.py
`50%` of new lines are covered (`83.33%` of the complete file).
Missing lines: `5`

### codebase/other.py
`100%` of new lines are covered (`100%` of the complete file).

</details>
<!-- foo -->"""
    assert result == expected


def test_template__no_new_lines_with_coverage(coverage_obj):
    diff_cov = coverage.DiffCoverage(
        total_num_lines=0,
        total_num_violations=0,
        total_percent_covered=decimal.Decimal("1"),
        num_changed_lines=39,
        files={},
    )

    result = template.get_comment_markdown(
        coverage=coverage_obj,
        diff_coverage=diff_cov,
        previous_coverage_rate=decimal.Decimal("1.0"),
        marker="<!-- foo -->",
        base_template=template.read_template_file("comment.md.j2"),
    )
    expected = """## Coverage report
The coverage rate went from `100%` to `75%` :arrow_down:
The branch rate is `50%`.

_None of the new lines are part of the tested code. Therefore, there is no coverage data about them._


<!-- foo -->"""
    assert result == expected


def test_template__no_branch_no_previous(coverage_obj_no_branch, diff_coverage_obj):
    result = template.get_comment_markdown(
        coverage=coverage_obj_no_branch,
        diff_coverage=diff_coverage_obj,
        previous_coverage_rate=None,
        marker="<!-- foo -->",
        base_template=template.read_template_file("comment.md.j2"),
    )
    expected = """## Coverage report
> **Note**
> No coverage data of the default branch was found for comparison. A possible reason for this is that the coverage action has not yet run after a push event and the data is therefore not yet initialized.

The coverage rate is `75%`.

`80%` of new lines are covered.

<details>
<summary>Diff Coverage details (click to unfold)</summary>

### codebase/code.py
`80%` of new lines are covered (`75%` of the complete file).
Missing lines: `7`, `9`

</details>
<!-- foo -->"""
    assert result == expected


def test_read_template_file():
    assert template.read_template_file("comment.md.j2").startswith(
        "{% block title %}## Coverage report{% if subproject_id %}"
    )


def test_template__no_marker(coverage_obj, diff_coverage_obj):
    with pytest.raises(template.MissingMarker):
        template.get_comment_markdown(
            coverage=coverage_obj,
            diff_coverage=diff_coverage_obj,
            previous_coverage_rate=decimal.Decimal("0.92"),
            base_template=template.read_template_file("comment.md.j2"),
            marker="<!-- foo -->",
            custom_template="""foo bar""",
        )


def test_template__broken_template(coverage_obj, diff_coverage_obj):
    with pytest.raises(template.TemplateError):
        template.get_comment_markdown(
            coverage=coverage_obj,
            diff_coverage=diff_coverage_obj,
            previous_coverage_rate=decimal.Decimal("0.92"),
            base_template=template.read_template_file("comment.md.j2"),
            marker="<!-- foo -->",
            custom_template="""{% extends "foo" %}""",
        )


@pytest.mark.parametrize(
    "value, displayed_coverage",
    [
        ("0.83", "83%"),
        ("0.99999", "99.99%"),
        ("0.00001", "0%"),
        ("0.0501", "5.01%"),
        ("1", "100%"),
        ("0.8392", "83.92%"),
    ],
)
def test_pct(value, displayed_coverage):
    assert template.pct(decimal.Decimal(value)) == displayed_coverage


def test_uptodate():
    assert template.uptodate() is True


@pytest.mark.parametrize(
    "marker_id, result",
    [
        (None, "<!-- This comment was produced by python-coverage-comment-action -->"),
        (
            "foo",
            "<!-- This comment was produced by python-coverage-comment-action (id: foo) -->",
        ),
    ],
)
def test_get_marker(marker_id, result):
    assert template.get_marker(marker_id=marker_id) == result
