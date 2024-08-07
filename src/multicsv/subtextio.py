from typing import TextIO, List, Optional, Type, Iterable
import io
import os
from .exceptions import OpOnClosedError, \
    InvalidWhenceError, InvalidSubtextCoordinates, \
    BaseMustBeReadable, BaseMustBeSeakable, \
    StartsBeyondBaseContent, BaseIOClosed


class SubTextIO(TextIO):
    """
    SubTextIO provides an interface for reading, writing, and
    manipulating a specified subsection of a base TextIO object. This
    class allows for convenient and isolated operations within a given
    range of the base TextIO buffer, while efficiently buffering
    content to minimize repeated seeks.

    Purpose:
    --------
    The primary aim of SubTextIO is to allow for editing, reading, and
    writing operations on a specific segment of a TextIO object
    without affecting other parts. This can be particularly useful in
    scenarios where parts of a large text file need to be updated or
    read independently.

    Structure:
    ----------
    - The class initializes by reading and storing the relevant
      segment of the base TextIO into an in-memory buffer.
    - Operations (read, write, seek, etc.) are done on this buffer.
    - Changes are committed back to the base TextIO when the `flush`
      or `close` method is called.

    Use Cases:
    ----------
    - Editing a specific section of a configuration file or log
      without loading the entire file.
    - Concurrent processing on different segments of a large file.
    - Efficiently managing memory and I/O operations for large-scale
      text processing tasks.

    Interface Functions:
    --------------------
    - `read(size: int = -1) -> str`: Reads a specified number of
      characters from the buffer.
    - `readline(limit: int = -1) -> str`: Reads and returns one line
      from the buffer.
    - `readlines(hint: int = -1) -> List[str]`: Reads and returns all
      remaining lines from the buffer.
    - `write(s: str) -> int`: Writes a string to the buffer.
    - `writelines(lines: List[str]) -> None`: Writes a list of lines
      to the buffer.
    - `truncate(size: int) -> int`: Resizes the section.
    - `seek(offset: int, whence: int = 0) -> int`: Moves the buffer's
      current position.
    - `tell() -> int`: Returns the current position in the buffer.
    - `flush() -> None`: Writes the buffer content back to the base
      TextIO object.
    - `close() -> None`: Flushes the buffer and closes this IO object.
    - Context Management Support: Allows for usage with `with`
      statement for automatic resource management.

    Examples:
    ---------
    ```python
    import io
    from subtextio import SubTextIO

    base_text = io.StringIO("Hello\nWorld\nThis\nIs\nA\nTest\n")
    sub_text = SubTextIO(base_text, start=6, end=21)

    # Should output 'World\n'
    print("Reading first line:", sub_text.readline())
    # Should output 'This\nIs\n'
    print("Reading rest within range:", sub_text.read())

    sub_text.seek(0)
    sub_text.write("NewContent")  # Overwrites 'World\nThis\n'
    sub_text.seek(0)
    # Should output 'NewContentIs\n'
    print("After write operation:", sub_text.read())

    sub_text.delete_section()
    sub_text.write("Overwritten")
    sub_text.seek(0)
    # Should output 'Overwritten'
    print("After delete and write operation:", sub_text.read())

    # Make sure changes are committed to the base TextIO
    sub_text.flush()
    # Should reflect changes in original buffer
    print("Base IO after SubTextIO flush:", base_text.getvalue())
    ```

    Caveats:
    --------
    - Writing to and reading from the base TextIO when it is used in SubTextIO
      can lead to unexpected results.
    - SubTextIO loads the subsection into memory. Thus be cautious
      of buffer size when working with very large files.
    - Always ensure to call `flush` or use context management to
      commit changes back to the base TextIO.
    """

    def __init__(self, base_io: TextIO, start: int, end: int):
        self._initialized = False
        self._base_io = base_io
        self._start = start
        self._end = end
        self._position = 0  # Position within the SubTextIO
        self._closed = base_io.closed
        self._buffer = ""

        if end < start or start < 0:
            raise InvalidSubtextCoordinates(
                f"Invalid range [{start},{end}] passed to SubTextIO.")

        if not base_io.seekable():
            raise BaseMustBeSeakable("Base io must be seekable.")

        if end > start and not base_io.readable():
            # TODO: losen this requirement because if we override by
            # the same length, then we dont need to read.
            raise BaseMustBeReadable("Base io must be readable"
                                     " if existing content is to be modified.")

        self._load()
        self._initial_length = self.buffer_length
        self._initialized = True

    def _load(self) -> None:
        """
        Load the relevant part of the base_io into the buffer.
        """

        base_initial_position = self._base_io.tell()

        #
        # Below we try to avoid calling `base_io.read()` as much as possible.
        #
        try:
            self._base_io.seek(0, os.SEEK_END)
            base_last_position = self._base_io.tell()

            if self.start > base_last_position:
                raise StartsBeyondBaseContent(
                    "Start position is greater than base TextIO length.")

            if self.end > self.start:
                self._base_io.seek(self.end)
                base_final_position = self._base_io.tell()
                self.is_at_end = base_final_position == base_last_position

                if self.end < base_last_position:
                    self._base_io.seek(self.start)
                    self._buffer = self._base_io.read(self.end - self.start)
                else:
                    self._buffer = ""
            else:
                self._buffer = ""
                base_final_position = self.start
                self._base_io.seek(0, os.SEEK_END)
                self.is_at_end = base_final_position == self._base_io.tell()
        finally:
            self._base_io.seek(base_initial_position)

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    @property
    def buffer_length(self) -> int:
        return len(self._buffer)

    @property
    def mode(self) -> str:
        return self._base_io.mode

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def encoding(self) -> str:
        return self._base_io.encoding

    def read(self, size: int = -1) -> str:
        self._check_closed()

        if size < 0 or size > self.buffer_length - self._position:
            size = self.buffer_length - self._position

        result = self._buffer[self._position:self._position + size]
        self._position += len(result)
        return result

    def readline(self, limit: int = -1) -> str:
        self._check_closed()

        if self._position >= self.buffer_length:
            return ''

        newline_pos = self._buffer.find('\n', self._position)
        if newline_pos == -1 or newline_pos >= self.buffer_length:
            newline_pos = self.buffer_length

        if limit < 0 or limit > newline_pos - self._position:
            limit = newline_pos - self._position + 1

        result = self._buffer[self._position:self._position + limit]
        self._position += len(result)
        return result

    def readlines(self, hint: int = -1) -> List[str]:
        """
        The `hint` argument in the `readlines` method of the `TextIO`
        interface serves as a performance hint rather than a strict
        limit. It indicates the approximate number of bytes to read
        from the file. If the hint is positive, the implementation may
        read more than the hint value to complete a line but will aim
        to read at least as many bytes as specified by the hint.
        """

        self._check_closed()

        remaining_buffer = self._buffer[self._position:]
        lines = remaining_buffer.splitlines(keepends=True)
        read_size = 0
        result = []

        for line in lines:
            result.append(line)
            read_size += len(line)
            if 0 <= hint <= read_size:
                break

        self._position += read_size
        return result

    def write(self, s: str) -> int:
        self._check_closed()

        pre = self._buffer[:self._position]
        post = self._buffer[self._position + len(s):]
        self._buffer = pre + s + post

        written = len(s)
        self._position += written

        return written

    def writelines(self, lines: Iterable[str]) -> None:
        for line in lines:
            self.write(line)

    def truncate(self, size: Optional[int] = None) -> int:
        self._check_closed()

        if size is None:
            end = self._position
        else:
            end = size

        self._buffer = self._buffer[:end]
        return self.buffer_length

    def close(self) -> None:
        if not self._closed:
            try:
                self.flush()
            finally:
                self._closed = True

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        self._check_closed()

        if whence == os.SEEK_SET:  # Absolute positioning
            target = offset
        elif whence == os.SEEK_CUR:  # Relative to current position
            target = self._position + offset
        elif whence == os.SEEK_END:  # Relative to the end
            target = self.buffer_length + offset
        else:
            raise InvalidWhenceError(
                f"Invalid value for whence: {repr(whence)}")

        self._position = max(0, min(target, self.buffer_length))
        return self._position

    def tell(self) -> int:
        self._check_closed()
        return self._position

    def flush(self) -> None:
        if not self._closed:
            base_initial_position = self._base_io.tell()
            try:
                if self.buffer_length == self._initial_length \
                   or self.is_at_end:
                    self._base_io.seek(self.start)
                    self._base_io.write(self._buffer)
                else:
                    self._base_io.seek(self.end)
                    content_after = self._base_io.read()

                    self._base_io.seek(self.start)
                    self._base_io.write(self._buffer + content_after)

                self._base_io.flush()
            finally:
                self._base_io.seek(base_initial_position)

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:
        raise io.UnsupportedOperation("Not a filesystem descriptor.")

    def readable(self) -> bool:
        return self._base_io.readable()

    def writable(self) -> bool:
        return self._base_io.writable()

    def seekable(self) -> bool:
        return True

    def _check_closed(self) -> None:
        """
        Helper method to verify if the IO object is closed.
        """

        if self._closed:
            raise OpOnClosedError("I/O operation on closed file.")

    def __iter__(self) -> 'SubTextIO':
        return self

    def __next__(self) -> str:
        if self._position < self.buffer_length:
            return self.readline()
        else:
            raise StopIteration

    def __enter__(self) -> 'SubTextIO':
        return self

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[object]) -> None:
        self.close()

    def __del__(self) -> None:
        if self._initialized:
            try:
                self.close()
            except BaseIOClosed:
                pass
