from __future__ import annotations

from collections.abc import Callable

from coverage_comment import main


def main_call(name: str, main_func: Callable[[], None] = main.main):
    if name == "__main__":
        main_func()


main_call(name=__name__)
