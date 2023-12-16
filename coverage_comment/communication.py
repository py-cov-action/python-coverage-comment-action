from __future__ import annotations

import pathlib

from coverage_comment import files, template


def get_readme_and_log(
    image_urls: files.ImageURLs,
    readme_url: str,
    html_report_url: str,
    markdown_report: str,
    is_public: bool,
    subproject_id: str | None = None,
) -> tuple[files.WriteFile, str]:
    readme_markdown = template.get_readme_markdown(
        is_public=is_public,
        readme_url=readme_url,
        markdown_report=markdown_report,
        html_report_url=html_report_url,
        direct_image_url=image_urls["direct"],
        endpoint_image_url=image_urls["endpoint"],
        dynamic_image_url=image_urls["dynamic"],
        subproject_id=subproject_id,
    )
    log_message = template.get_log_message(
        is_public=is_public,
        readme_url=readme_url,
        html_report_url=html_report_url,
        direct_image_url=image_urls["direct"],
        endpoint_image_url=image_urls["endpoint"],
        dynamic_image_url=image_urls["dynamic"],
        subproject_id=subproject_id,
    )
    readme = files.WriteFile(
        path=pathlib.Path("README.md"),
        contents=readme_markdown,
    )
    return readme, log_message
