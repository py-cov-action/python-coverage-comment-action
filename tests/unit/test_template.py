from __future__ import annotations

import decimal
import pathlib

import pytest

from coverage_comment import coverage, template


def test_get_comment_markdown(coverage_obj, diff_coverage_obj):
    files, total = template.select_files(
        coverage=coverage_obj,
        diff_coverage=diff_coverage_obj,
        previous_coverage=coverage_obj,
        max_files=25,
    )
    result = (
        template.get_comment_markdown(
            coverage=coverage_obj,
            previous_coverage=coverage_obj,
            diff_coverage=diff_coverage_obj,
            files=files,
            count_files=total,
            max_files=25,
            previous_coverage_rate=decimal.Decimal("0.92"),
            minimum_green=decimal.Decimal("100"),
            minimum_orange=decimal.Decimal("70"),
            marker="<!-- foo -->",
            github_host="https://github.com",
            repo_name="org/repo",
            pr_number=1,
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

    expected = ["92%", "62.5%", "60%", "bar", "<!-- foo -->"]

    assert result == expected


def test_template(coverage_obj, diff_coverage_obj):
    files, total = template.select_files(
        coverage=coverage_obj,
        diff_coverage=diff_coverage_obj,
        previous_coverage=None,
        max_files=25,
    )
    result = template.get_comment_markdown(
        coverage=coverage_obj,
        diff_coverage=diff_coverage_obj,
        previous_coverage=None,
        previous_coverage_rate=decimal.Decimal("0.92"),
        minimum_green=decimal.Decimal("79"),
        minimum_orange=decimal.Decimal("40"),
        files=files,
        count_files=total,
        max_files=25,
        github_host="https://github.com",
        repo_name="org/repo",
        pr_number=5,
        base_template=template.read_template_file("comment.md.j2"),
        marker="<!-- foo -->",
        subproject_id="foo",
        custom_template="""{% extends "base" %}
        {% block emoji_coverage_down %}:sob:{% endblock emoji_coverage_down %}
        """,
    )
    print(result)
    expected = """## Coverage report (foo)


<img title="Coverage for the whole project went from 92% to 62.5%" src="https://img.shields.io/badge/Coverage%20evolution-92%25%20%3E%2062%25-red.svg"> <img title="60% of the statement lines added by this PR are covered" src="https://img.shields.io/badge/PR%20Coverage-60%25-orange.svg"><details><summary>Click to see where and how coverage changed</summary><table><thead>
  <tr><th>File</th><th>Statements</th><th>Missing</th><th>Coverage</th><th>Coverage<br>(new stmts)</th><th>Lines missing</th></tr>
</thead>
<tbody><tr>
<td colspan="6">&nbsp;&nbsp;<b>codebase</b></td><tr>
<td>&nbsp;&nbsp;<a href="https://github.com/org/repo/pull/5/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3">code.py</a></td>
<td align="center"><a href="https://github.com/org/repo/pull/5/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="This PR adds 21 statements to codebase/code.py. The file did not seem to exist on the base branch." src="https://img.shields.io/badge/21-%28%2B21%29-007ec6.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/5/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="This PR adds 6 statements missing coverage to codebase/code.py. The file did not seem to exist on the base branch." src="https://img.shields.io/badge/6-%28%2B6%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/5/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="The coverage rate of codebase/code.py is 62.5% (15/21). The file did not seem to exist on the base branch." src="https://img.shields.io/badge/62%25-%2815/21%29-orange.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/5/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="In this PR, 5 new statements are added to codebase/code.py, 3 of which are covered (60%)." src="https://img.shields.io/badge/60%25-%283/5%29-orange.svg"></a></td><td><a href="https://github.com/org/repo/pull/5/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3R6-R8">6-8</a></td></tbody>
<tfoot>
<tr>
<td><b>Project Total</b></td>
<td align="center"><a href="https://github.com/org/repo/pull/5/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="This PR adds 21 statements to the whole project. The file did not seem to exist on the base branch." src="https://img.shields.io/badge/21-%28%2B21%29-007ec6.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/5/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="This PR adds 6 statements missing coverage to the whole project. The file did not seem to exist on the base branch." src="https://img.shields.io/badge/6-%28%2B6%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/5/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="The coverage rate of the whole project is 62.5% (15/21). The file did not seem to exist on the base branch." src="https://img.shields.io/badge/62%25-%2815/21%29-orange.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/5/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="In this PR, 5 new statements are added to the whole project, 3 of which are covered (60%)." src="https://img.shields.io/badge/60%25-%283/5%29-orange.svg"></a></td><td>&nbsp;</td>
</tr>
</tfoot>
</table>

<sub>

This report was generated by [python-coverage-comment-action](https://github.com/py-cov-action/python-coverage-comment-action)

</sub>
</details>



<!-- foo -->"""
    assert result == expected


def test_template_full(make_coverage, make_coverage_and_diff):
    previous_cov = make_coverage(
        """
        # file: codebase/code.py
        1 covered
        2 covered
        3
        4 missing
        5 covered
        6 covered
        7
        8
        9 covered
        # file: codebase/other.py
        1 covered
        2 covered
        3 covered
        4 covered
        5 covered
        6 covered
        # file: codebase/third.py
        1 covered
        2 covered
        3 covered
        4 covered
        5 covered
        6 missing
        7 missing
        """
    )
    cov, diff_cov = make_coverage_and_diff(
        """
        # file: codebase/code.py
        1 covered
        2 covered
        3
        4
        5 covered
        6 covered
        7
        8
        9 covered
        10
        11
        + 12 missing
        + 13 missing
        + 14 missing
        + 15 covered
        + 16 covered
        + 17
        + 18
        + 19
        + 20
        + 21
        + 22 missing
        # file: codebase/other.py
        1 covered
        2 covered
        3 covered
        # file: codebase/third.py
        1 covered
        2 covered
        3 covered
        4 covered
        5 covered
        6 covered
        7 covered
        """
    )

    files, total = template.select_files(
        coverage=cov,
        diff_coverage=diff_cov,
        previous_coverage=previous_cov,
        max_files=25,
    )

    result = template.get_comment_markdown(
        coverage=cov,
        diff_coverage=diff_cov,
        previous_coverage=previous_cov,
        files=files,
        count_files=total,
        max_files=25,
        previous_coverage_rate=decimal.Decimal("11") / decimal.Decimal("12"),
        minimum_green=decimal.Decimal("100"),
        minimum_orange=decimal.Decimal("70"),
        marker="<!-- foo -->",
        github_host="https://github.com",
        repo_name="org/repo",
        pr_number=12,
        base_template=template.read_template_file("comment.md.j2"),
    )
    expected = """## Coverage report


<img title="Coverage for the whole project went from 91.66% to 80.95%" src="https://img.shields.io/badge/Coverage%20evolution-91%25%20%3E%2080%25-red.svg"> <img title="33.33% of the statement lines added by this PR are covered" src="https://img.shields.io/badge/PR%20Coverage-33%25-red.svg"><details><summary>Click to see where and how coverage changed</summary><table><thead>
  <tr><th>File</th><th>Statements</th><th>Missing</th><th>Coverage</th><th>Coverage<br>(new stmts)</th><th>Lines missing</th></tr>
</thead>
<tbody><tr>
<td colspan="6">&nbsp;&nbsp;<b>codebase</b></td><tr>
<td>&nbsp;&nbsp;<a href="https://github.com/org/repo/pull/12/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3">code.py</a></td>

<td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="This PR adds 5 to the number of statements in codebase/code.py, taking it from 6 to 11." src="https://img.shields.io/badge/11-%28%2B5%29-007ec6.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="This PR adds 3 to the number of statements missing coverage in codebase/code.py, taking it from 1 to 4." src="https://img.shields.io/badge/4-%28%2B3%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="This PR removes 19.70 percentage points from the coverage rate in codebase/code.py, taking it from 83.33% (5/6) to 63.63% (7/11)." src="https://img.shields.io/badge/63%25-%285/6%20%3E%207/11%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="In this PR, 6 new statements are added to codebase/code.py, 2 of which are covered (33.33%)." src="https://img.shields.io/badge/33%25-%282/6%29-red.svg"></a></td><td><a href="https://github.com/org/repo/pull/12/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3R12-R14">12-14</a>, <a href="https://github.com/org/repo/pull/12/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3R22-R22">22</a></td><tr>
<td>&nbsp;&nbsp;<a href="https://github.com/org/repo/pull/12/files#diff-30cad827f61772ec66bb9ef8887058e6d8443a2afedb331d800feaa60228a26e">other.py</a></td>

<td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-30cad827f61772ec66bb9ef8887058e6d8443a2afedb331d800feaa60228a26e"><img title="This PR removes 3 from the number of statements in codebase/other.py, taking it from 6 to 3." src="https://img.shields.io/badge/3-%28--3%29-49c2ee.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-30cad827f61772ec66bb9ef8887058e6d8443a2afedb331d800feaa60228a26e"><img title="This PR doesn't change the number of statements missing coverage in codebase/other.py, which is 0." src="https://img.shields.io/badge/0-%28%C2%B10%29-lightgrey.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-30cad827f61772ec66bb9ef8887058e6d8443a2afedb331d800feaa60228a26e"><img title="This PR doesn't change the coverage rate in codebase/other.py, which is 100% (3/3)." src="https://img.shields.io/badge/100%25-%286/6%20%3E%203/3%29-lightgrey.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-30cad827f61772ec66bb9ef8887058e6d8443a2afedb331d800feaa60228a26e"><img title="This PR does not seem to add statements to codebase/other.py." src="https://img.shields.io/badge/N/A-grey.svg"></a></td><td></td><tr>
<td>&nbsp;&nbsp;<a href="https://github.com/org/repo/pull/12/files#diff-6da86228e0702d51c55944bde3e5224d3a78ac4f7ac6262230d457dd3cd3eb88">third.py</a></td>

<td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-6da86228e0702d51c55944bde3e5224d3a78ac4f7ac6262230d457dd3cd3eb88"><img title="This PR doesn't change the number of statements in codebase/third.py, which is 7." src="https://img.shields.io/badge/7-%28%C2%B10%29-5d89ba.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-6da86228e0702d51c55944bde3e5224d3a78ac4f7ac6262230d457dd3cd3eb88"><img title="This PR removes 2 from the number of statements missing coverage in codebase/third.py, taking it from 2 to 0." src="https://img.shields.io/badge/0-%28--2%29-brightgreen.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-6da86228e0702d51c55944bde3e5224d3a78ac4f7ac6262230d457dd3cd3eb88"><img title="This PR adds 28.57 percentage points to the coverage rate in codebase/third.py, taking it from 71.42% (5/7) to 100% (7/7)." src="https://img.shields.io/badge/100%25-%285/7%20%3E%207/7%29-brightgreen.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-6da86228e0702d51c55944bde3e5224d3a78ac4f7ac6262230d457dd3cd3eb88"><img title="This PR does not seem to add statements to codebase/third.py." src="https://img.shields.io/badge/N/A-grey.svg"></a></td><td></td></tbody>
<tfoot>
<tr>
<td><b>Project Total</b></td>

<td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="This PR adds 2 to the number of statements in the whole project, taking it from 19 to 21." src="https://img.shields.io/badge/21-%28%2B2%29-007ec6.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="This PR adds 1 to the number of statements missing coverage in the whole project, taking it from 3 to 4." src="https://img.shields.io/badge/4-%28%2B1%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="This PR removes 3.26 percentage points from the coverage rate in the whole project, taking it from 84.21% (16/19) to 80.95% (17/21)." src="https://img.shields.io/badge/80%25-%2816/19%20%3E%2017/21%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/12/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="In this PR, 6 new statements are added to the whole project, 2 of which are covered (33.33%)." src="https://img.shields.io/badge/33%25-%282/6%29-red.svg"></a></td><td>&nbsp;</td>
</tr>
</tfoot>
</table>

<sub>

This report was generated by [python-coverage-comment-action](https://github.com/py-cov-action/python-coverage-comment-action)

</sub>
</details>



<!-- foo -->"""
    print(result)
    assert result == expected


def test_template__no_previous(coverage_obj_no_branch, diff_coverage_obj):
    files, total = template.select_files(
        coverage=coverage_obj_no_branch,
        diff_coverage=diff_coverage_obj,
        previous_coverage=None,
        max_files=25,
    )
    result = template.get_comment_markdown(
        coverage=coverage_obj_no_branch,
        diff_coverage=diff_coverage_obj,
        previous_coverage_rate=None,
        previous_coverage=None,
        files=files,
        count_files=total,
        max_files=25,
        minimum_green=decimal.Decimal("100"),
        minimum_orange=decimal.Decimal("70"),
        marker="<!-- foo -->",
        github_host="https://github.com",
        repo_name="org/repo",
        pr_number=3,
        base_template=template.read_template_file("comment.md.j2"),
    )
    expected = """## Coverage report


<img title="Coverage for the whole project is 50%. Previous coverage rate is not available, cannot report on evolution." src="https://img.shields.io/badge/Coverage-50%25-red.svg"> <img title="60% of the statement lines added by this PR are covered" src="https://img.shields.io/badge/PR%20Coverage-60%25-red.svg"><details><summary>Click to see where and how coverage changed</summary><table><thead>
  <tr><th>File</th><th>Statements</th><th>Missing</th><th>Coverage</th><th>Coverage<br>(new stmts)</th><th>Lines missing</th></tr>
</thead>
<tbody><tr>
<td colspan="6">&nbsp;&nbsp;<b>codebase</b></td><tr>
<td>&nbsp;&nbsp;<a href="https://github.com/org/repo/pull/3/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3">code.py</a></td>
<td align="center"><a href="https://github.com/org/repo/pull/3/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="This PR adds 8 statements to codebase/code.py. The file did not seem to exist on the base branch." src="https://img.shields.io/badge/8-%28%2B8%29-007ec6.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/3/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="This PR adds 4 statements missing coverage to codebase/code.py. The file did not seem to exist on the base branch." src="https://img.shields.io/badge/4-%28%2B4%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/3/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="The coverage rate of codebase/code.py is 50% (4/8). The file did not seem to exist on the base branch." src="https://img.shields.io/badge/50%25-%284/8%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/3/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3"><img title="In this PR, 5 new statements are added to codebase/code.py, 3 of which are covered (60%)." src="https://img.shields.io/badge/60%25-%283/5%29-red.svg"></a></td><td><a href="https://github.com/org/repo/pull/3/files#diff-c05d5557f0c1ff3761df2f49e3b541cfc161f4f0d63e2a66d568f090065bc3d3R6-R8">6-8</a></td></tbody>
<tfoot>
<tr>
<td><b>Project Total</b></td>
<td align="center"><a href="https://github.com/org/repo/pull/3/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="This PR adds 8 statements to the whole project. The file did not seem to exist on the base branch." src="https://img.shields.io/badge/8-%28%2B8%29-007ec6.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/3/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="This PR adds 4 statements missing coverage to the whole project. The file did not seem to exist on the base branch." src="https://img.shields.io/badge/4-%28%2B4%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/3/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="The coverage rate of the whole project is 50% (4/8). The file did not seem to exist on the base branch." src="https://img.shields.io/badge/50%25-%284/8%29-red.svg"></a></td><td align="center"><a href="https://github.com/org/repo/pull/3/files#diff-4b0bf2efa3367c0072ac2bf1e234e703dc46b47aaa4fe9d3b01737b1a15752b1"><img title="In this PR, 5 new statements are added to the whole project, 3 of which are covered (60%)." src="https://img.shields.io/badge/60%25-%283/5%29-red.svg"></a></td><td>&nbsp;</td>
</tr>
</tfoot>
</table>

<sub>

This report was generated by [python-coverage-comment-action](https://github.com/py-cov-action/python-coverage-comment-action)

</sub>
</details>



<!-- foo -->"""
    print(result)
    assert result == expected


def test_template__max_files(coverage_obj_more_files, diff_coverage_obj_more_files):
    files, total = template.select_files(
        coverage=coverage_obj_more_files,
        diff_coverage=diff_coverage_obj_more_files,
        previous_coverage=None,
        max_files=25,
    )
    result = template.get_comment_markdown(
        coverage=coverage_obj_more_files,
        diff_coverage=diff_coverage_obj_more_files,
        previous_coverage=None,
        files=files,
        count_files=total,
        previous_coverage_rate=decimal.Decimal("0.92"),
        minimum_green=decimal.Decimal("79"),
        minimum_orange=decimal.Decimal("40"),
        github_host="https://github.com",
        repo_name="org/repo",
        pr_number=5,
        max_files=1,
        base_template=template.read_template_file("comment.md.j2"),
        marker="<!-- foo -->",
        subproject_id="foo",
        custom_template="""{% extends "base" %}
        {% block emoji_coverage_down %}:sob:{% endblock emoji_coverage_down %}
        """,
    )
    print(result)

    assert "The report is truncated to 1 files out of 2." in result


def test_template__no_max_files(coverage_obj_more_files, diff_coverage_obj_more_files):
    files, total = template.select_files(
        coverage=coverage_obj_more_files,
        diff_coverage=diff_coverage_obj_more_files,
        previous_coverage=None,
        max_files=25,
    )
    result = template.get_comment_markdown(
        coverage=coverage_obj_more_files,
        diff_coverage=diff_coverage_obj_more_files,
        previous_coverage=None,
        files=files,
        count_files=total,
        previous_coverage_rate=decimal.Decimal("0.92"),
        minimum_green=decimal.Decimal("79"),
        minimum_orange=decimal.Decimal("40"),
        github_host="https://github.com",
        repo_name="org/repo",
        pr_number=5,
        max_files=None,
        base_template=template.read_template_file("comment.md.j2"),
        marker="<!-- foo -->",
        subproject_id="foo",
        custom_template="""{% extends "base" %}
        {% block emoji_coverage_down %}:sob:{% endblock emoji_coverage_down %}
        """,
    )
    print(result)

    assert "The report is truncated" not in result
    assert "code.py" in result
    assert "other.py" in result


def test_template__no_files(coverage_obj, diff_coverage_obj_more_files):
    diff_coverage = coverage.DiffCoverage(
        total_num_lines=0,
        total_num_violations=0,
        total_percent_covered=decimal.Decimal("1"),
        num_changed_lines=0,
        files={},
    )
    result = template.get_comment_markdown(
        coverage=coverage_obj,
        diff_coverage=diff_coverage,
        previous_coverage=coverage_obj,
        files=[],
        count_files=0,
        previous_coverage_rate=decimal.Decimal("0.92"),
        minimum_green=decimal.Decimal("79"),
        minimum_orange=decimal.Decimal("40"),
        github_host="https://github.com",
        repo_name="org/repo",
        pr_number=5,
        max_files=25,
        base_template=template.read_template_file("comment.md.j2"),
        marker="<!-- foo -->",
        subproject_id="foo",
        custom_template="""{% extends "base" %}
        {% block emoji_coverage_down %}:sob:{% endblock emoji_coverage_down %}
        """,
    )
    print(result)

    assert (
        "_This PR does not seem to contain any modification to coverable code."
        in result
    )
    assert "code.py" not in result
    assert "other.py" not in result


def test_read_template_file():
    assert template.read_template_file("comment.md.j2").startswith(
        "{%- block title -%}## Coverage report{%- if subproject_id %}"
    )


def test_template__no_marker(coverage_obj, diff_coverage_obj):
    with pytest.raises(template.MissingMarker):
        template.get_comment_markdown(
            coverage=coverage_obj,
            previous_coverage=None,
            files=[],
            count_files=0,
            max_files=25,
            diff_coverage=diff_coverage_obj,
            previous_coverage_rate=decimal.Decimal("0.92"),
            minimum_green=decimal.Decimal("100"),
            minimum_orange=decimal.Decimal("70"),
            github_host="https://github.com",
            repo_name="org/repo",
            pr_number=1,
            base_template=template.read_template_file("comment.md.j2"),
            marker="<!-- foo -->",
            custom_template="""foo bar""",
        )


def test_template__broken_template(coverage_obj, diff_coverage_obj):
    with pytest.raises(template.TemplateError):
        template.get_comment_markdown(
            coverage=coverage_obj,
            previous_coverage=None,
            diff_coverage=diff_coverage_obj,
            files=[],
            count_files=0,
            max_files=25,
            previous_coverage_rate=decimal.Decimal("0.92"),
            minimum_green=decimal.Decimal("100"),
            minimum_orange=decimal.Decimal("70"),
            github_host="https://github.com",
            repo_name="org/repo",
            pr_number=1,
            base_template=template.read_template_file("comment.md.j2"),
            marker="<!-- foo -->",
            custom_template="""{% extends "foo" %}""",
        )


@pytest.mark.parametrize(
    "value, displayed_coverage",
    [
        (decimal.Decimal("0.83"), "83%"),
        (decimal.Decimal("0.99999"), "99.99%"),
        (decimal.Decimal("0.00001"), "0%"),
        (decimal.Decimal("0.0501"), "5.01%"),
        (decimal.Decimal("1"), "100%"),
        (decimal.Decimal("0.2"), "20%"),
        (decimal.Decimal("0.8392"), "83.92%"),
    ],
)
def test_pct(value, displayed_coverage):
    assert template.pct(value) == displayed_coverage


@pytest.mark.parametrize(
    "number, singular, plural, expected",
    [
        (1, "", "s", ""),
        (2, "", "s", "s"),
        (0, "", "s", "s"),
        (1, "y", "ies", "y"),
        (2, "y", "ies", "ies"),
    ],
)
def test_pluralize(number, singular, plural, expected):
    assert (
        template.pluralize(number=number, singular=singular, plural=plural) == expected
    )


@pytest.mark.parametrize(
    "filepath, lines, expected",
    [
        (
            pathlib.Path("tests/conftest.py"),
            None,
            "https://github.com/py-cov-action/python-coverage-comment-action/pull/33/files#diff-e52e4ddd58b7ef887ab03c04116e676f6280b824ab7469d5d3080e5cba4f2128",
        ),
        (
            pathlib.Path("main.py"),
            (12, 15),
            "https://github.com/py-cov-action/python-coverage-comment-action/pull/33/files#diff-b10564ab7d2c520cdd0243874879fb0a782862c3c902ab535faabe57d5a505e1R12-R15",
        ),
        (
            pathlib.Path("codebase/other.py"),
            (22, 22),
            "https://github.com/py-cov-action/python-coverage-comment-action/pull/33/files#diff-30cad827f61772ec66bb9ef8887058e6d8443a2afedb331d800feaa60228a26eR22-R22",
        ),
    ],
)
def test_get_file_url(filepath, lines, expected):
    result = template.get_file_url(
        filename=filepath,
        lines=lines,
        github_host="https://github.com",
        repo_name="py-cov-action/python-coverage-comment-action",
        pr_number=33,
    )
    assert result == expected


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


@pytest.mark.parametrize(
    "previous_code, current_code_and_diff, max_files, expected_files, expected_total",
    [
        pytest.param(
            """
            # file: a.py
            1 covered
            """,
            """
            # file: a.py
            1 covered
            """,
            2,
            [],
            0,
            id="unmodified",
        ),
        pytest.param(
            """
            # file: a.py
            1 covered
            """,
            """
            # file: a.py
            1
            2 covered
            """,
            2,
            [],
            0,
            id="info_did_not_change",
        ),
        pytest.param(
            """
            # file: a.py
            1 covered
            """,
            """
            # file: a.py
            1 missing
            """,
            2,
            ["a.py"],
            1,
            id="info_did_change",
        ),
        pytest.param(
            """
            # file: a.py
            1 covered
            """,
            """
            # file: a.py
            + 1 covered
            """,
            2,
            ["a.py"],
            1,
            id="with_diff",
        ),
        pytest.param(
            """
            # file: b.py
            1 covered
            # file: a.py
            1 covered
            """,
            """
            # file: b.py
            + 1 covered
            # file: a.py
            + 1 covered
            """,
            2,
            ["a.py", "b.py"],
            2,
            id="ordered",
        ),
        pytest.param(
            """
            # file: a.py
            1 covered
            # file: b.py
            1 covered
            """,
            """
            # file: a.py
            1 covered
            2 covered
            # file: b.py
            1 missing
            """,
            1,
            ["b.py"],
            2,
            id="truncated",
        ),
        pytest.param(
            """
            # file: a.py
            1 covered
            # file: c.py
            1 covered
            # file: b.py
            1 covered
            """,
            """
            # file: a.py
            + 1 covered
            # file: c.py
            1 missing
            # file: b.py
            1 missing
            """,
            2,
            ["b.py", "c.py"],
            3,
            id="truncated_and_ordered",
        ),
        pytest.param(
            """
            # file: a.py
            1 covered
            # file: c.py
            1 covered
            # file: b.py
            1 covered
            """,
            """
            # file: a.py
            1
            2 covered
            # file: c.py
            + 1 covered
            # file: b.py
            1 covered
            1 covered
            """,
            2,
            ["b.py", "c.py"],
            2,
            id="truncated_and_ordered_sort_order_advanced",
        ),
        pytest.param(
            """
            # file: a.py
            1 covered
            # file: b.py
            1 covered
            """,
            """
            # file: a.py
            1 covered
            2 covered
            # file: b.py
            1 missing
            """,
            None,
            ["a.py", "b.py"],
            2,
            id="max_none",
        ),
    ],
)
def test_select_files(
    make_coverage,
    make_coverage_and_diff,
    previous_code,
    current_code_and_diff,
    max_files,
    expected_files,
    expected_total,
):
    previous_cov = make_coverage(previous_code)
    cov, diff_cov = make_coverage_and_diff(current_code_and_diff)

    files, total = template.select_files(
        coverage=cov,
        diff_coverage=diff_cov,
        previous_coverage=previous_cov,
        max_files=max_files,
    )
    assert [str(e.path) for e in files] == expected_files
    assert total == expected_total


def test_select_files__no_previous(
    make_coverage_and_diff,
):
    cov, diff_cov = make_coverage_and_diff(
        """
        # file: a.py
        1 covered
        + 1 missing
        """
    )

    files, total = template.select_files(
        coverage=cov,
        diff_coverage=diff_cov,
        previous_coverage=None,
        max_files=1,
    )
    assert [str(e.path) for e in files] == ["a.py"]
    assert total == 1


@pytest.mark.parametrize(
    "previous_code, current_code_and_diff, expected_new_missing, expected_added, expected_new_covered",
    [
        pytest.param(
            """
            # file: a.py
            1 covered
            2 missing
            """,
            """
            # file: a.py
            + 1
            2 covered
            + 3 missing
            + 4 missing
            + 5 covered
            """,
            1,
            3,
            1,
            id="added_code",
        ),
        pytest.param(
            """
            # file: a.py
            1 covered
            2 missing
            3 covered
            4 missing
            """,
            """
            # file: a.py
            + 1 missing
            """,
            1,
            1,
            2,
            id="removed_code",
        ),
    ],
)
def test_sort_order(
    make_coverage_and_diff,
    make_coverage,
    previous_code,
    current_code_and_diff,
    expected_new_missing,
    expected_added,
    expected_new_covered,
):
    previous_cov = make_coverage(previous_code)
    cov, diff_cov = make_coverage_and_diff(current_code_and_diff)
    path = pathlib.Path("a.py")
    file_info = template.FileInfo(
        path=path,
        coverage=cov.files[path],
        diff=diff_cov.files[path],
        previous=previous_cov.files[path],
    )
    new_missing, added, new_covered = template.sort_order(file_info=file_info)
    assert new_missing == expected_new_missing
    assert added == expected_added
    assert new_covered == expected_new_covered


def test_sort_order__none(make_coverage):
    cov = make_coverage(
        """
        # file: a.py
        1 covered
        """
    )
    file_info = template.FileInfo(
        path=pathlib.Path("a.py"),
        coverage=cov.files[pathlib.Path("a.py")],
        diff=None,
        previous=None,
    )
    new_missing, added, new_covered = template.sort_order(file_info=file_info)
    assert new_missing == 0
    assert added == 0
    assert new_covered == 1


def test_get_readme_markdown():
    result = template.get_readme_markdown(
        is_public=True,
        readme_url="https://example.com",
        markdown_report="...markdown report...",
        direct_image_url="https://example.com/direct.png",
        html_report_url="https://example.com/report.html",
        dynamic_image_url="https://example.com/dynamic.png",
        endpoint_image_url="https://example.com/endpoint.png",
        subproject_id="foo",
    )
    assert result.startswith("# Repository Coverage (foo)")


def test_get_log_message():
    result = template.get_log_message(
        is_public=True,
        readme_url="https://example.com",
        direct_image_url="https://example.com/direct.png",
        html_report_url="https://example.com/report.html",
        dynamic_image_url="https://example.com/dynamic.png",
        endpoint_image_url="https://example.com/endpoint.png",
        subproject_id="foo",
    )
    assert result.startswith("Coverage info for foo:")


@pytest.mark.parametrize(
    "value, expected",
    [
        (0, "0"),
        (1, "1"),
        (999, "999"),
        (1_042, "1.0k"),
        (9_900, "9.9k"),
        (12_345, "12k"),
        (999_999, "1000k"),
        (1_234_567, "1M"),
    ],
)
def test_compact(value, expected):
    assert template.compact(value) == expected
