from __future__ import annotations

import logging
import re

from coverage_comment import log_utils


def test_level_mapping__all_supported():
    ignored = {
        logging.getLevelName("NOTSET"),
        logging.getLevelName("TRACE"),
    }
    assert (
        set(log_utils.LEVEL_MAPPING)
        == set(logging.getLevelNamesMapping().values()) - ignored
    )


def test__github_formatter():
    logs = []

    class TestHandler(logging.Handler):
        def emit(self, record):
            logs.append(self.format(record))

    logger = logging.Logger("test", level="DEBUG")
    handler = TestHandler()
    handler.setFormatter(log_utils.GitHubFormatter())
    logger.addHandler(handler)

    logger.debug("a debug message")
    logger.info("a notice message")
    logger.warning("a warning message")
    logger.error("an error message")
    logger.critical("an error message")
    try:
        0 / 0
    except Exception:
        logger.exception("an exception")

    logs = "\n".join(logs)
    logs = re.sub(r"""File ".+", line \d+""", """File "foo.py", line 42""", logs)

    expected = """
::debug::a debug message
::notice::a notice message
::warning::a warning message
::error::an error message
::error::an error message
::error::an exception%0ATraceback (most recent call last):%0A  File "foo.py", line 42, in test__github_formatter%0A    0 / 0%0A    ~~^~~%0AZeroDivisionError: division by zero""".strip()

    assert logs == expected
