from __future__ import annotations

import logging

logger = logging.getLogger("coverage_comment")


def __getattr__(name):
    return getattr(logger, name)
