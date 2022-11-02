from coverage_comment import annotations


def test_annotations(coverage_obj, capsys):
    annotations.create_pr_annotations(annotation_type="warning", coverage=coverage_obj)

    expected = """::group::Annotations of lines with missing coverage
::warning file=codebase/code.py,line=7::This line has no coverage
::warning file=codebase/code.py,line=9::This line has no coverage
::endgroup::"""
    output = capsys.readouterr()
    assert output.out.strip() == expected


def test_annotations_several_files(coverage_obj_many_missing_lines, capsys):
    annotations.create_pr_annotations(
        annotation_type="notice", coverage=coverage_obj_many_missing_lines
    )

    expected = """::group::Annotations of lines with missing coverage
::notice file=codebase/main.py,line=3::This line has no coverage
::notice file=codebase/main.py,line=7::This line has no coverage
::notice file=codebase/main.py,line=13::This line has no coverage
::notice file=codebase/main.py,line=21::This line has no coverage
::notice file=codebase/main.py,line=123::This line has no coverage
::notice file=codebase/caller.py,line=13::This line has no coverage
::notice file=codebase/caller.py,line=21::This line has no coverage
::notice file=codebase/caller.py,line=212::This line has no coverage
::endgroup::"""
    output = capsys.readouterr()
    assert output.out.strip() == expected
