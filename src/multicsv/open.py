
from typing import Union, Literal, BinaryIO, NoReturn
from pathlib import Path

from .file import MultiCSVFile


OpenPath = Union[str, int, bytes, Path]

# Textual mode strings accepted by multicsv_open.
OpenMode = Literal["r", "w", "a", "x", "r+", "w+", "a+", "x+"]
OpenBinaryMode = Literal["rb", "wb", "ab", "xb", "r+b", "w+b", "a+b", "x+b"]


def _to_binary_mode(mode: OpenMode) -> OpenBinaryMode:
    """Translate a textual mode string to its binary equivalent.

    Strips any ``'t'`` flag and appends ``'b'`` if not already present.
    Examples: ``"r"`` \u2192 ``"rb"``, ``"w+"`` \u2192 ``"w+b"``,
    ``"a+t"`` \u2192 ``"a+b"``.
    """

    if mode == "r":
        return "rb"
    elif mode == "w":
        return "wb"
    elif mode == "a":
        return "ab"
    elif mode == "x":
        return "xb"
    elif mode == "r+":
        return "r+b"
    elif mode == "w+":
        return "w+b"
    elif mode == "a+":
        return "a+b"
    elif mode == "x+":
        return "x+b"
    else:
        _other: NoReturn = mode
        raise ValueError(f"Invalid mode: {mode!r}")


def multicsv_open(path: OpenPath,
                  mode: OpenMode = "r",
                  encoding: str = 'utf-8') -> MultiCSVFile:
    """Open a multi-CSV file at *path*.

    *mode* is a standard text-mode string (``"r"``, ``"w"``, ``"a"``,
    ``"x"``, or any of those with ``"+"``).  The file is always opened in
    binary mode internally; the text encoding is handled by
    :class:`~multicsv.file.MultiCSVFile` using *encoding*.
    """
    file = open(path, mode=_to_binary_mode(mode))
    return MultiCSVFile(file, own=True, encoding=encoding)


def multicsv_wrap(file: BinaryIO, encoding: str = 'utf-8') -> MultiCSVFile:
    return MultiCSVFile(file, encoding=encoding)
