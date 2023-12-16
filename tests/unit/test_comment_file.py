from __future__ import annotations

from coverage_comment import comment_file


def test_comment_file(tmp_path):
    path = tmp_path / "foo.txt"
    comment_file.store_file(filename=path, content="foo")

    assert path.read_text() == "foo"
