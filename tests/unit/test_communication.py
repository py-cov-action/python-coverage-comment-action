import pytest

from coverage_comment import communication


@pytest.mark.parametrize("is_public", [True, False])
def test_get_readme_and_log(is_public):

    readme_file, log = communication.get_readme_and_log(
        image_urls={
            "direct": "https://a",
            "endpoint": "https://b",
            "dynamic": "https://c",
        },
        readme_url="https://readme",
        is_public=is_public,
    )

    readme = readme_file.contents

    assert str(readme_file.path) == "README.md"

    assert "# Coverage data" in readme

    assert "[![Coverage badge](https://a)](https://readme)" in readme

    assert ("[![Coverage badge](https://b)](https://readme)" in readme) is (is_public)

    assert ("[![Coverage badge](https://c)](https://readme)" in readme) is (is_public)

    assert "https://a" in log

    assert "https://readme" in log

    assert ("https://b" in log) is (is_public)

    assert ("https://c" in log) is (is_public)
