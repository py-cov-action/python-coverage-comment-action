import pathlib

from coverage_comment import files

README_CONTENTS = """
# Coverage data

This branch is just here to hold coverage data. It's part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action.

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge]({direct_image_url})]({readme_url})

This is the one to use if your repository is private or if you don't want to customize anything.
""".strip()

PUBLIC_README_CONTENTS = """
### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge]({endpoint_image_url})]({readme_url})

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge]({dynamic_image_url})]({readme_url})

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.
""".strip()

LOG_CONTENTS = """You can use the following URLs to display your badge:

Badge SVG available at:
    {direct_image_url}""".strip()

PUBLIC_LOG_CONTENTS = """
Badge from shields endpoint is easier to customize but doesn't work with private repo:
    {endpoint_image_url}

Badge from shields dynamic url (less useful but you never know):
    {dynamic_image_url}""".strip()

LOG_CONCLUSION = """
See more details and ready-to-copy-paste-markdown at {readme_url}""".strip()


def get_readme_and_log(
    image_urls: files.ImageURLs,
    readme_url: str,
    is_public: bool,
) -> tuple[files.FileWithPath, str]:
    """
    The text we display in the GitHub Actions Log, and what we write in the
    branch readme when initializing the coverage data branch is quite similar.
    This function generate both chunks of text with the hope that they'll stay
    in sync.
    """
    readme_contents_parts = [
        README_CONTENTS.format(
            readme_url=readme_url,
            direct_image_url=image_urls["direct"],
        )
    ]
    if is_public:
        readme_contents_parts.append(
            PUBLIC_README_CONTENTS.format(
                readme_url=readme_url,
                endpoint_image_url=image_urls["endpoint"],
                dynamic_image_url=image_urls["dynamic"],
            )
        )
    readme = files.FileWithPath(
        path=pathlib.Path("README.md"),
        contents="\n\n".join(readme_contents_parts),
    )

    log_message_parts = [
        LOG_CONTENTS.format(direct_image_url=image_urls["direct"]),
        LOG_CONCLUSION.format(readme_url=readme_url),
    ]

    if is_public:
        public_part = PUBLIC_LOG_CONTENTS.format(
            endpoint_image_url=image_urls["endpoint"],
            dynamic_image_url=image_urls["dynamic"],
        )
        log_message_parts.insert(1, public_part)

    log_message = "\n\n".join(log_message_parts)

    return readme, log_message
