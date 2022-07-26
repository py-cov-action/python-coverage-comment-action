import pytest

from coverage_comment import template


def test_get_markdown_comment(coverage_obj, diff_coverage_obj):
    result = (
        template.get_markdown_comment(
            coverage=coverage_obj,
            diff_coverage=diff_coverage_obj,
            previous_coverage_rate=0.92,
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
        "<!-- This comment was produced by python-coverage-comment-action -->",
    ]

    assert result == expected


def test_template(coverage_obj, diff_coverage_obj):
    result = template.get_markdown_comment(
        coverage=coverage_obj,
        diff_coverage=diff_coverage_obj,
        previous_coverage_rate=0.92,
        base_template=template.read_template_file(),
        custom_template="""{% extends "base" %}
        {% block emoji_coverage_down %}:sob:{% endblock emoji_coverage_down %}
        """,
    )
    expected = """## Coverage report
The coverage rate went from `92%` to `75%` :sob:
The branch rate is `50%`.

`80%` of new lines are covered.

<details>
<summary>Diff Coverage details (click to unfold)</summary>

### codebase/code.py
`80%` of new lines are covered (`75%` of the complete file).

Missing lines: `7`, `9`

</details>
<!-- This comment was produced by python-coverage-comment-action -->"""
    assert result == expected


def test_template__no_branch_no_previous(coverage_obj_no_branch, diff_coverage_obj):
    result = template.get_markdown_comment(
        coverage=coverage_obj_no_branch,
        diff_coverage=diff_coverage_obj,
        previous_coverage_rate=None,
        base_template=template.read_template_file(),
    )
    expected = """## Coverage report
The coverage rate is `75%`.

`80%` of new lines are covered.

<details>
<summary>Diff Coverage details (click to unfold)</summary>

### codebase/code.py
`80%` of new lines are covered (`75%` of the complete file).

Missing lines: `7`, `9`

</details>
<!-- This comment was produced by python-coverage-comment-action -->"""
    assert result == expected


def test_read_template_file():
    assert template.read_template_file().startswith(
        "{% block title %}## Coverage report{% endblock title %}"
    )


def test_template__no_marker(coverage_obj, diff_coverage_obj):

    with pytest.raises(template.MissingMarker):
        template.get_markdown_comment(
            coverage=coverage_obj,
            diff_coverage=diff_coverage_obj,
            previous_coverage_rate=0.92,
            base_template=template.read_template_file(),
            custom_template="""foo bar""",
        )


def test_template__broken_template(coverage_obj, diff_coverage_obj):

    with pytest.raises(template.TemplateError):
        template.get_markdown_comment(
            coverage=coverage_obj,
            diff_coverage=diff_coverage_obj,
            previous_coverage_rate=0.92,
            base_template=template.read_template_file(),
            custom_template="""{% extends "foo" %}""",
        )


def test_pct():
    assert template.pct(0.83) == "83%"


def test_uptodate():
    assert template.uptodate() is True
