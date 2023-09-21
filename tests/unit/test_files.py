import decimal
import pathlib

from coverage_comment import files


def test_write_file(tmp_path):
    files.WriteFile(path=tmp_path / "a", contents="foo").apply()

    assert (tmp_path / "a").read_text() == "foo"


def test_replace_dir(tmp_path):
    (tmp_path / "foo").mkdir()
    (tmp_path / "foo/foofile").touch()
    (tmp_path / "bar").mkdir()
    (tmp_path / "bar/barfile").touch()

    files.ReplaceDir(path=(tmp_path / "bar"), source=(tmp_path / "foo")).apply()

    assert not (tmp_path / "foo").exists()
    assert (tmp_path / "bar").exists()
    assert (tmp_path / "bar/foofile").exists()
    assert not (tmp_path / "bar/barfile").exists()


def test_compute_files(session):
    session.register(
        "GET", "https://img.shields.io/static/v1?label=Coverage&message=12%25&color=red"
    )(text="foo")

    result = files.compute_files(
        line_rate=decimal.Decimal("0.1234"),
        raw_coverage_data={"foo": ["bar", "bar2"]},
        coverage_path=pathlib.Path("."),
        minimum_green=decimal.Decimal("25"),
        minimum_orange=decimal.Decimal("70"),
        http_session=session,
    )
    expected = [
        files.WriteFile(
            path=pathlib.Path("endpoint.json"),
            contents='{"schemaVersion": 1, "label": "Coverage", "message": "12%", "color": "red"}',
        ),
        files.WriteFile(
            path=pathlib.Path("data.json"),
            contents='{"coverage": 12.34, "raw_data": {"foo": ["bar", "bar2"]}, "coverage_path": "."}',
        ),
        files.WriteFile(path=pathlib.Path("badge.svg"), contents="foo"),
    ]
    assert result == expected


def test_compute_datafile():
    assert (
        files.compute_datafile(
            line_rate=decimal.Decimal("12.34"),
            raw_coverage_data={"meta": {"version": "5.5"}},
            coverage_path=pathlib.Path("./src/code"),
        )
        == """{"coverage": 12.34, "raw_data": {"meta": {"version": "5.5"}}, "coverage_path": "src/code"}"""
    )


def test_parse_datafile():
    assert files.parse_datafile(contents="""{"coverage": 12.34}""") == decimal.Decimal(
        "0.1234"
    )


def test_get_urls():
    def getter(path):
        return f"https://{path}"

    urls = files.get_urls(url_getter=getter)

    assert urls == {
        "direct": "https://badge.svg",
        "dynamic": "https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fendpoint.json",
        "endpoint": "https://img.shields.io/endpoint?url=https://endpoint.json",
    }


def test_get_coverage_html_files(mocker, in_tmp_path):
    def gen_side_effect(destination, coverage_path):
        (destination / ".gitignore").touch()
        (destination / "index.html").touch()

    gen = mocker.patch(
        "coverage_comment.coverage.generate_coverage_html_files",
        side_effect=gen_side_effect,
    )
    gen_dir = in_tmp_path / "gen"
    gen_dir.mkdir()
    rep = files.get_coverage_html_files(gen_dir=gen_dir, coverage_path=".")
    (source_htmlcov,) = gen_dir.iterdir()

    assert rep == files.ReplaceDir(path=pathlib.Path("htmlcov"), source=source_htmlcov)

    assert gen.called is True
    assert not (source_htmlcov / "gitignore").exists()
