from coverage_comment import annotations


def test_annotations(diff_coverage_obj, capsys):
    annotations.create_pr_annotations(
        annotation_type="warning", coverage=diff_coverage_obj
    )

    expected = """::group::Annotations of lines with missing coverage
::warning file=codebase/code.py,line=7::This line has no coverage
::warning file=codebase/code.py,line=9::This line has no coverage
::endgroup::"""
    output = capsys.readouterr()
    assert output.out.strip() == expected


def test_annotations_several_files(diff_coverage_obj, capsys):
    annotations.create_pr_annotations(
        annotation_type="notice", coverage=diff_coverage_obj
    )

    expected = """::group::Annotations of lines with missing coverage
::notice file=codebase/code.py,line=7::This line has no coverage
::notice file=codebase/code.py,line=9::This line has no coverage
::endgroup::"""
    output = capsys.readouterr()
    assert output.out.strip() == expected
