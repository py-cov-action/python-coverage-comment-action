from coverage_comment import communication


def test_get_readme_and_log__public():
    readme_file, log = communication.get_readme_and_log(
        is_public=True,
        image_urls={
            "direct": "https://a",
            "endpoint": "https://b",
            "dynamic": "https://c",
        },
        readme_url="https://readme",
        html_report_url="https://html_report",
        markdown_report="**Hello report!**",
    )

    readme = readme_file.contents

    assert str(readme_file.path) == "README.md"

    assert "# Repository Coverage" in readme

    assert "[![Coverage badge](https://a)](https://html_report)" in readme

    assert "[![Coverage badge](https://b)](https://html_report)" in readme

    assert "[![Coverage badge](https://c)](https://html_report)" in readme

    assert "https://a" in log

    assert "https://readme" in log

    assert "https://b" in log

    assert "https://c" in log


def test_get_readme_and_log__private():
    readme_file, log = communication.get_readme_and_log(
        is_public=False,
        image_urls={
            "direct": "https://a",
            "endpoint": "https://b",
            "dynamic": "https://c",
        },
        readme_url="https://readme",
        html_report_url="https://html_report",
        markdown_report="**Hello report!**",
    )

    readme = readme_file.contents

    assert str(readme_file.path) == "README.md"

    assert "# Repository Coverage" in readme

    assert "[![Coverage badge](https://a)](https://readme)" in readme

    assert "https://b" not in readme

    assert "https://c" not in readme

    assert "https://a" in log

    assert "https://readme" in log

    assert "https://b" not in log

    assert "https://c" not in log
