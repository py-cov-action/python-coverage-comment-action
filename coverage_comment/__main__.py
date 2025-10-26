from __future__ import annotations

from coverage_comment import main


def main_call(name: str):
    if name == "__main__":
        main.main()


main_call(name=__name__)
