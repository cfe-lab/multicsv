from __future__ import annotations

from typing import TYPE_CHECKING, BinaryIO
import io
import os

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer, WriteableBuffer


class SubBinaryIO(io.BufferedIOBase):
    """
    A seekable read/write view of a contiguous byte range ``[start, end)``
    within a *base_io* binary file.

    SubBinaryIO does **not** copy bytes into memory.  Every read, write, and
    seek operation is forwarded directly to *base_io* after translating the
    local offset into an absolute file position.  This means:

    * The view is cheaply created even for multi-gigabyte files.
    * Writes to the view are immediately visible through *base_io* and vice-
      versa (they share the same underlying file descriptor).
    * ``tell()`` always returns a plain ``int`` byte offset (never an opaque
      codec-state cookie), making it safe to use as a boundary marker when
      slicing a file into sections.

    Coordinates
    -----------
    *start* and *end* are **absolute** byte positions in *base_io* measured
    from the beginning of the file (as returned by ``base_io.tell()`` after
    ``base_io.seek(0)``).  The view covers the half-open interval
    ``[start, end)``.  An empty view (``start == end``) is allowed.

    The internal *position* is always **relative** to *start* and runs in
    ``[0, end - start]``.  In other words, ``tell()`` returns ``0`` just
    after construction and ``end - start`` once all bytes have been read.

    Closing
    -------
    ``close()`` marks this view as closed but does **not** close *base_io*.
    The owner is responsible for the lifetime of *base_io*.

    Compatibility with ``io.TextIOWrapper``
    ----------------------------------------
    SubBinaryIO satisfies every requirement of ``io.BufferedIOBase`` so it
    can be wrapped directly:

    >>> import io
    >>> raw = io.BytesIO(b"hello\\nworld\\n")
    >>> sub = SubBinaryIO(raw, start=6, end=12)   # b"world\\n"
    >>> text = io.TextIOWrapper(sub, encoding="utf-8")
    >>> text.read()
    'world\\n'

    Because ``tell()`` returns a plain integer, wrapping with
    ``TextIOWrapper`` is safe regardless of the encoding of *base_io* –
    there are no opaque codec-state cookies.

    Read / write example
    --------------------
    >>> raw = io.BytesIO(b"AAAABBBBCCCC")
    >>> sub = SubBinaryIO(raw, start=4, end=8)    # b"BBBB"
    >>> sub.read(2)
    b'BB'
    >>> sub.write(b"XX")                          # overwrites the 3rd and 4th B
    2
    >>> raw.seek(0); raw.read()
    b'AAAABBXXCCCC'
    """

    def __init__(self, base_io: BinaryIO, start: int, end: int) -> None:
        super().__init__()
        self._base_io = base_io
        self._start = start
        self._end = end
        self._position = 0  # relative to _start

    # ------------------------------------------------------------------ #
    # IO[bytes] protocol attributes                                        #
    # ------------------------------------------------------------------ #

    @property
    def name(self) -> str:
        """Nominal name of this byte-range view.

        Returns a fixed string since the view has no file-system path of its
        own.  The property exists to satisfy the ``typing.IO[bytes]`` protocol
        required by ``io.TextIOWrapper``.
        """
        return "<SubBinaryIO>"

    @property
    def mode(self) -> str:
        """Access mode string (always ``'rb+'``).

        SubBinaryIO supports both reading and writing so ``'rb+'`` is the
        appropriate description.  The property exists to satisfy the
        ``typing.IO[bytes]`` protocol required by ``io.TextIOWrapper``.
        """
        return "rb+"

    # ------------------------------------------------------------------ #
    # Capability flags                                                     #
    # ------------------------------------------------------------------ #

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @property
    def _abs_pos(self) -> int:
        """Absolute position in *base_io* corresponding to the current local position."""
        return self._start + self._position

    @property
    def _region_size(self) -> int:
        """Length of the byte region this view covers."""
        return self._end - self._start

    def _remaining(self) -> int:
        """Number of bytes left between the current position and the end of the region."""
        return max(0, self._region_size - self._position)

    # ------------------------------------------------------------------ #
    # Read operations                                                      #
    # ------------------------------------------------------------------ #

    def readinto(self, b: WriteableBuffer) -> int:
        """Read up to ``len(b)`` bytes into *b*, capped to the region boundary."""
        self._checkClosed()
        mv = memoryview(b)
        want = min(len(mv), self._remaining())
        if want == 0:
            return 0
        self._base_io.seek(self._abs_pos)
        chunk = self._base_io.read(want)
        n = len(chunk)
        mv[:n] = chunk
        self._position += n
        return n

    def read(self, size: int | None = -1) -> bytes:
        """Read at most *size* bytes from the region (all remaining if *size* is ``None`` or negative)."""
        self._checkClosed()
        effective = -1 if size is None else size
        want = self._remaining() if effective < 0 else min(effective, self._remaining())
        if want == 0:
            return b""
        self._base_io.seek(self._abs_pos)
        chunk = self._base_io.read(want)
        self._position += len(chunk)
        return chunk

    def read1(self, size: int | None = -1) -> bytes:
        """Read up to *size* bytes in a single underlying call.

        Mirrors ``io.BufferedIOBase.read1()``, required by ``io.TextIOWrapper``.
        For a stream with no internal read-ahead buffer this is identical to
        :meth:`read`.
        """
        return self.read(size)

    def readline(self, size: int | None = -1) -> bytes:
        """Read up to the next ``\\n`` (inclusive) or EOF, capped by *size* and the region end.

        The scan is performed by reading the region incrementally in small
        chunks so that only a single line's worth of data is held in memory at
        any time.
        """
        self._checkClosed()
        effective = -1 if size is None else size
        limit = self._remaining() if effective < 0 else min(effective, self._remaining())
        if limit == 0:
            return b""
        # Scan for a newline inside the region without loading the whole region.
        self._base_io.seek(self._abs_pos)
        line = self._base_io.read(limit)
        nl = line.find(b"\n")
        if nl != -1:
            line = line[: nl + 1]
        self._position += len(line)
        return line

    # ------------------------------------------------------------------ #
    # Write operations                                                     #
    # ------------------------------------------------------------------ #

    def write(self, b: ReadableBuffer) -> int:
        """Write *b* into the region at the current position.

        Data is written directly to *base_io* at ``start + position``.
        Writing beyond the current region end is **not** allowed; any
        excess bytes are silently dropped and only the bytes that fit
        within ``[start, end)`` are written.  Returns the number of bytes
        actually written.
        """
        self._checkClosed()
        data = bytes(b)
        space = self._remaining()
        if space == 0:
            return 0
        chunk = data[:space]
        self._base_io.seek(self._abs_pos)
        n = self._base_io.write(chunk)
        self._position += n
        return n

    def truncate(self, size: int | None = None) -> int:
        """Truncate the *logical* view to *size* bytes from the start of the region.

        This updates the ``end`` boundary of the view; it does **not**
        truncate *base_io*.
        """
        self._checkClosed()
        if size is None:
            size = self._position
        self._end = self._start + max(0, size)
        if self._position > size:
            self._position = size
        return self._region_size

    # ------------------------------------------------------------------ #
    # Position                                                             #
    # ------------------------------------------------------------------ #

    def seek(self, pos: int, whence: int = os.SEEK_SET) -> int:
        """Seek to *pos* within the region.

        All three standard *whence* values are supported:
        ``SEEK_SET`` (0), ``SEEK_CUR`` (1), and ``SEEK_END`` (2).
        The position is clamped to ``[0, region_size]``; seeking before
        the start of the region is silently clamped to 0.
        """
        self._checkClosed()
        if whence == os.SEEK_SET:
            target = pos
        elif whence == os.SEEK_CUR:
            target = self._position + pos
        elif whence == os.SEEK_END:
            target = self._region_size + pos
        else:
            raise OSError(f"Invalid whence value: {whence!r}")
        self._position = max(0, min(target, self._region_size))
        return self._position

    def tell(self) -> int:
        """Return the current position as a byte offset from the start of the region.

        Unlike ``io.TextIOWrapper.tell()`` the value is always a plain
        integer and never an opaque codec-state cookie.
        """
        self._checkClosed()
        return self._position

    # ------------------------------------------------------------------ #
    # Flush / close                                                        #
    # ------------------------------------------------------------------ #

    def flush(self) -> None:
        """Flush the underlying *base_io* without closing it."""
        if not self.closed:
            self._base_io.flush()

    def close(self) -> None:
        """Mark this view as closed.

        Does **not** close *base_io*; the owner is responsible for the
        lifetime of the underlying file object.
        """
        super().close()
