import pathlib


def store_file(filename: pathlib.Path, content: str):
    filename.write_text(content)
