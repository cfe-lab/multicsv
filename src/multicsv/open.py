
from typing import Union, Literal
import os

from .file import MultiCSVFile


OpenPath = Union[str, os.PathLike[str], int, bytes, os.PathLike[bytes]]


def multicsv_open(path: OpenPath,
                  mode: Literal["r", "w", "a", "x", "r+", "w+", "a+", "x+",
                                "rt", "wt", "at", "xt", "r+t", "w+t", "a+t",
                                "x+t"] = "rt") \
                  -> MultiCSVFile:

    file = open(path, mode=mode)
    return MultiCSVFile(file, own=True)
