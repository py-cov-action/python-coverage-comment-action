import pathlib


def store_file(filename: str, content: str):
    pathlib.Path(filename).write_text(content)
