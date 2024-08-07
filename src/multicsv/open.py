
from typing import Union, Iterator, Literal
import os
from contextlib import contextmanager

from .file import MultiCSVFile


OpenPath = Union[str, os.PathLike[str], int, bytes, os.PathLike[bytes]]


@contextmanager
def multicsv_open(path: OpenPath,
                  mode: Literal["r", "w", "a", "x", "r+", "w+", "a+", "x+",
                                "rt", "wt", "at", "xt", "r+t", "w+t", "a+t",
                                "x+t"] = "rt") \
                  -> Iterator[MultiCSVFile]:

    with open(path, mode=mode) as file:
        with MultiCSVFile(file) as ret:
            yield ret
