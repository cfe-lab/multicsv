
from typing import Union, Literal, BinaryIO, cast
from pathlib import Path

from .file import MultiCSVFile


OpenPath = Union[str, int, bytes, Path]

# Textual mode strings accepted by multicsv_open.
OpenMode = Literal["r", "w", "a", "x", "r+", "w+", "a+", "x+"]


def _to_binary_mode(mode: str) -> str:
    """Translate a textual mode string to its binary equivalent.

    Strips any ``'t'`` flag and appends ``'b'`` if not already present.
    Examples: ``"r"`` \u2192 ``"rb"``, ``"w+"`` \u2192 ``"w+b"``,
    ``"a+t"`` \u2192 ``"a+b"``.
    """
    m = mode.replace('t', '')
    if 'b' not in m:
        m += 'b'
    return m


def multicsv_open(path: OpenPath,
                  mode: OpenMode = "r",
                  encoding: str = 'utf-8') -> MultiCSVFile:
    """Open a multi-CSV file at *path*.

    *mode* is a standard text-mode string (``"r"``, ``"w"``, ``"a"``,
    ``"x"``, or any of those with ``"+"``).  The file is always opened in
    binary mode internally; the text encoding is handled by
    :class:`~multicsv.file.MultiCSVFile` using *encoding*.
    """
    file = cast(BinaryIO, open(path, mode=_to_binary_mode(mode)))
    return MultiCSVFile(file, own=True, encoding=encoding)


def multicsv_wrap(file: BinaryIO, encoding: str = 'utf-8') -> MultiCSVFile:
    return MultiCSVFile(file, encoding=encoding)
