import decimal
import pathlib

from coverage_comment import files


def test_compute_files(session):
    session.register(
        "GET", "https://img.shields.io/static/v1?label=Coverage&message=12%25&color=red"
    )(text="foo")

    result = files.compute_files(
        line_rate=decimal.Decimal("0.1234"),
        minimum_green=decimal.Decimal("25"),
        minimum_orange=decimal.Decimal("70"),
        http_session=session,
    )
    expected = [
        files.WriteFile(
            path=pathlib.Path("endpoint.json"),
            contents='{"schemaVersion": 1, "label": "Coverage", "message": "12%", "color": "red"}',
        ),
        files.WriteFile(path=pathlib.Path("data.json"), contents='{"coverage": 12.34}'),
        files.WriteFile(path=pathlib.Path("badge.svg"), contents="foo"),
    ]
    assert result == expected


def test_compute_datafile():
    assert (
        files.compute_datafile(line_rate=decimal.Decimal("12.34"))
        == """{"coverage": 12.34}"""
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
    gen = mocker.patch("coverage_comment.coverage.generate_coverage_html_files")
    cov = in_tmp_path / "htmlcov"
    cov.mkdir()
    gitignore = cov / ".gitignore"
    gitignore.touch()

    assert files.get_coverage_html_files() == files.FileWithPath(
        path=pathlib.Path("htmlcov"), contents=None
    )

    assert gen.called is True
    assert not gitignore.exists()
