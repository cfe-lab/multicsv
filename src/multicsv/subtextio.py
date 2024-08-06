
from typing import TextIO, List, Optional, Type, Iterable
import os


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
    - `delete_section() -> None`: Deletes the entire content of the
      subsection's buffer.
    - `seek(offset: int, whence: int = 0) -> int`: Moves the buffer's
      current position.
    - `tell() -> int`: Returns the current position in the buffer.
    - `flush() -> None`: Writes the buffer content back to the base
      TextIO object.
    - `close() -> None`: Flushes the buffer and closes the base TextIO
      object.
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
    - Ensure that the range specified by `start` and `end` does not
      overlap unintended sections of the text.
    - Be cautious of buffer size and memory usage when working with
      very large files.
    - Always ensure to call `flush` or use context management to
      commit changes back to the base TextIO.
    """

    def __init__(self, base_io: TextIO, start: int, end: int):
        self.base_io = base_io
        self.start = start
        self.end = end
        self.position = 0  # Position within the SubTextIO

        # Load the relevant part of the file into the buffer
        self.base_io.seek(self.start)
        self._buffer = self.base_io.read(self.end - self.start)
        self.length = len(self._buffer)
        self._closed = False

    @property
    def mode(self) -> str:
        return self.base_io.mode

    def read(self, size: int = -1) -> str:
        if self._closed:
            raise ValueError("I/O operation on closed file.")

        if size < 0 or size > self.length - self.position:
            size = self.length - self.position

        result = self._buffer[self.position:self.position + size]
        self.position += len(result)
        return result

    def readline(self, limit: int = -1) -> str:
        if self._closed:
            raise ValueError("I/O operation on closed file.")

        if self.position >= self.length:
            return ''

        newline_pos = self._buffer.find('\n', self.position)
        if newline_pos == -1 or newline_pos >= self.length:
            newline_pos = self.length

        if limit < 0 or limit > newline_pos - self.position:
            limit = newline_pos - self.position + 1

        result = self._buffer[self.position:self.position + limit]
        self.position += len(result)
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

        if self._closed:
            raise ValueError("I/O operation on closed file.")

        remaining_buffer = self._buffer[self.position:]
        lines = remaining_buffer.splitlines(keepends=True)
        read_size = 0
        result = []

        for line in lines:
            result.append(line)
            read_size += len(line)
            if 0 <= hint <= read_size:
                break

        self.position += read_size
        return result

    def write(self, s: str) -> int:
        if self._closed:
            raise ValueError("I/O operation on closed file.")

        pre = self._buffer[:self.position]
        post = self._buffer[self.position + len(s):]
        self._buffer = pre + s + post

        written = len(s)
        self.position += written

        self.length = max(self.position, self.length)
        return written

    def writelines(self, lines: Iterable[str]) -> None:
        for line in lines:
            self.write(line)

    def truncate(self, size: Optional[int] = None) -> int:
        if self._closed:
            raise ValueError("I/O operation on closed file.")

        if size is None:
            end = self.position
        else:
            end = size

        self._buffer = self._buffer[:end]
        self.length = len(self._buffer)
        return self.length

    def close(self) -> None:
        if not self._closed:
            self.flush()
            self._closed = True

    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
        if self._closed:
            raise ValueError("I/O operation on closed file.")

        if whence == os.SEEK_SET:  # Absolute positioning
            target = offset
        elif whence == os.SEEK_CUR:  # Relative to current position
            target = self.position + offset
        elif whence == os.SEEK_END:  # Relative to the end
            target = self.length + offset
        else:
            raise ValueError(f"Invalid value for whence: {repr(whence)}")

        self.position = max(0, min(target, self.length))
        return self.position

    def tell(self) -> int:
        if self._closed:
            raise ValueError("I/O operation on closed file.")

        return self.position

    def flush(self) -> None:
        if not self._closed:
            self.base_io.seek(0)
            content_before = self.base_io.read(self.start)
            self.base_io.seek(self.end)
            content_after = self.base_io.read()

            self.base_io.seek(0)
            self.base_io.write(content_before + self._buffer + content_after)
            self.base_io.flush()

    def __iter__(self) -> 'SubTextIO':
        return self

    def __next__(self) -> str:
        if self.position < self.length:
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
