
from typing import Union, Literal, BinaryIO
from pathlib import Path

from .file import MultiCSVFile


OpenPath = Union[str, int, bytes, Path]


def multicsv_open(path: OpenPath,
                  mode: Literal["rb", "wb", "ab", "xb",
                                "r+b", "w+b", "a+b", "x+b"] = "rb",
                  encoding: str = 'utf-8') -> MultiCSVFile:

    file = open(path, mode=mode)
    return MultiCSVFile(file, own=True, encoding=encoding)


def multicsv_wrap(file: BinaryIO, encoding: str = 'utf-8') -> MultiCSVFile:
    return MultiCSVFile(file, encoding=encoding)
