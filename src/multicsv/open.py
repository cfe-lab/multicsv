
from typing import Union, Literal, TextIO
from pathlib import Path

from .file import MultiCSVFile


OpenPath = Union[str, int, bytes, Path]


def multicsv_open(path: OpenPath,
                  mode: Literal["r", "w", "a", "x", "r+", "w+", "a+", "x+",
                                "rt", "wt", "at", "xt", "r+t", "w+t", "a+t",
                                "x+t"] = "rt") \
                  -> MultiCSVFile:

    file = open(path, mode=mode)
    return MultiCSVFile(file, own=True)


def multicsv_wrap(file: TextIO) -> MultiCSVFile:
    return MultiCSVFile(file)
