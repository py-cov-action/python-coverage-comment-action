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


def test_annotations_several_files(diff_coverage_obj_many_missing_lines, capsys):
    annotations.create_pr_annotations(
        annotation_type="notice", coverage=diff_coverage_obj_many_missing_lines
    )

    expected = """::group::Annotations of lines with missing coverage
::notice file=codebase/code.py,line=3::This line has no coverage
::notice file=codebase/code.py,line=5::This line has no coverage
::notice file=codebase/code.py,line=21::This line has no coverage
::notice file=codebase/code.py,line=111::This line has no coverage
::notice file=codebase/helper.py,line=19::This line has no coverage
::notice file=codebase/helper.py,line=22::This line has no coverage
::notice file=codebase/files.py,line=120::This line has no coverage
::notice file=codebase/files.py,line=121::This line has no coverage
::notice file=codebase/files.py,line=122::This line has no coverage
::endgroup::"""
    output = capsys.readouterr()
    assert output.out.strip() == expected
