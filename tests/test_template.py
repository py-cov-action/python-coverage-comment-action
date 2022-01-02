from coverage_comment import template


def test_get_markdown_comment(coverage_obj, diff_coverage_obj):
    result = template.get_markdown_comment(
        coverage=coverage_obj,
        diff_coverage=diff_coverage_obj,
        previous_coverage_rate=0.92,
        template="""
        {{ previous_coverage_rate | pct }}
        {{ coverage.info.percent_covered | pct }}
        {{ diff_coverage.total_percent_covered | pct }}
        """.strip(),
    ).split()

    expected = ["92%", "75%", "80%"]

    assert result == expected


def test_template(coverage_obj, diff_coverage_obj):
    result = template.get_markdown_comment(
        coverage=coverage_obj,
        diff_coverage=diff_coverage_obj,
        previous_coverage_rate=0.92,
        template=template.read_template_file(),
    )
    expected = """## Coverage report
The coverage rate went from `92%` to `75%` :arrow_down:
The branch rate is `50%`

`80%` of new lines are covered.

<details>
<summary>Diff Coverage details (click to unfold)</summary>

### codebase/code.py
`80%` of new lines are covered (`75%` of the complete file)

Missing lines: `7`, `9`



</details><!-- This comment was produced by python-coverage-comment-action -->"""
    assert result == expected


def test_template__no_branch_no_previous(coverage_obj_no_branch, diff_coverage_obj):
    result = template.get_markdown_comment(
        coverage=coverage_obj_no_branch,
        diff_coverage=diff_coverage_obj,
        previous_coverage_rate=None,
        template=template.read_template_file(),
    )
    expected = """## Coverage report
The coverage rate is `75%`


`80%` of new lines are covered.

<details>
<summary>Diff Coverage details (click to unfold)</summary>

### codebase/code.py
`80%` of new lines are covered (`75%` of the complete file)

Missing lines: `7`, `9`



</details><!-- This comment was produced by python-coverage-comment-action -->"""
    assert result == expected


def test_read_template_file():
    assert template.read_template_file().startswith("## Coverage report")


def test_pct():
    assert template.pct(0.83) == "83%"
