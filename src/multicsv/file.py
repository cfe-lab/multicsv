
from typing import BinaryIO, TextIO, Optional, Type, List, MutableMapping, \
    Iterator
import csv
import io
from .subbinaryio import SubBinaryIO
from .exceptions import OpOnClosedCSVFileError, CSVFileBaseIOClosed, \
    SectionNotFound
from .section import MultiCSVSection


class MultiCSVFile(MutableMapping[str, TextIO]):
    """
    MultiCSVFile provides an interface for reading, writing, and manipulating
    sections of a CSV file as individual TextIO objects. This class allows for
    convenient management of multiple independent sections within a single CSV
    file.

    Purpose:
    --------
    The primary aim of MultiCSVFile is to facilitate operations on
    distinct segments of a CSV file, allowing each segment to be
    treated as a TextIO object. This is particularly useful for
    handling CSV files structured with multiple sections, such as
    those containing configuration data, structured logs, or
    segment-wise data.

    Structure:
    ----------
    - The class initialises by reading the CSV file in binary mode and
      identifying sections encapsulated within bracketed headers
      (e.g. [section_name]).
    - Each section is represented by a MultiCSVSection whose descriptor is
      an io.TextIOWrapper wrapping a SubBinaryIO.  SubBinaryIO is a live view
      into the base file keyed by byte offsets, so tell() always returns a
      plain integer offset regardless of the file's encoding.
    - Operations like reading, writing, iterating, and deleting sections are
      supported.
    - Changes in sections are committed back to the base CSV file when
      the `flush` or `close` method is invoked.

    Use Cases:
    ----------
    - Efficient handling of configuration files with multiple
      independent segments.
    - Structured log files where each segment represents a distinct
      log category.
    - Processing large CSV files by logically splitting them into independent
      sections for easier manipulation.

    Interface Functions:
    --------------------
    - `__getitem__(key: str) -> TextIO`: Retrieves the TextIO object for the
      specified section.
    - `__setitem__(key: str, value: TextIO) -> None`: Sets the TextIO
      object for the specified section.
    - `__delitem__(key: str) -> None`: Deletes the specified section.
    - `__iter__() -> Iterator[str]`: Iterates over the section names.
    - `__len__() -> int`: Returns the number of sections.
    - `__contains__(key: object) -> bool`: Checks if a specific section exists.
    - `close() -> None`: Closes the MultiCSVFile and flushes any
      uncommitted changes.
    - `flush() -> None`: Commits changes in sections back to the base CSV file.
    - Context Management Support: Allows for usage with `with` statement for
      automatic resource management.

    Examples:
    ---------
    ```python
    import io
    from multicsv.file import MultiCSVFile

    # Initialize the MultiCSVFile with a base CSV byte stream
    csv_content = io.BytesIO(
        b"[section1]\\na,b,c\\n1,2,3\\n[section2]\\nd,e,f\\n4,5,6\\n")
    csv_file = MultiCSVFile(csv_content)

    # Accessing a section (returns TextIO decoded with the given encoding)
    section1 = csv_file["section1"]
    print(section1.read())  # Should output 'a,b,c\\n1,2,3\\n'

    # Adding a new section
    new_section = io.StringIO("g,h,i\\n7,8,9\\n")
    csv_file["section3"] = new_section
    csv_file.flush()

    # Verify the new section is added
    csv_content.seek(0)
    print(csv_content.read())
    ```

    Caveats:
    --------
    - The base BinaryIO must remain open for the lifetime of MultiCSVFile.
    - Always ensure to call `flush` or use context management to commit
      changes back to the base CSV file.
    - Mixing reads/writes on MultiCSVFile and the base BinaryIO directly
      may cause inconsistencies.
    """

    def __init__(self, file: BinaryIO, own: bool = False,
                 encoding: str = 'utf-8') -> None:
        self._initialized = False
        self._need_flush = False
        self._own_file = own
        self._file = file
        self._encoding = encoding
        self._closed = self._file.closed
        self._sections: List[MultiCSVSection] = []
        self._initialize_sections()
        self._initialized = True

    def __getitem__(self, key: str) -> TextIO:
        self._check_closed()

        for item in self._sections:
            if item.name == key:
                item.descriptor.seek(0)
                return item.descriptor

        raise SectionNotFound("MultiCSVFile does not "
                              f"have section named {key!r}.")

    def __setitem__(self, key: str, value: TextIO) -> None:
        self._check_closed()

        def make_section() -> MultiCSVSection:
            return MultiCSVSection(name=key, descriptor=value)

        for i, item in enumerate(self._sections):
            if item.name == key:
                self._sections[i] = make_section()
                self._need_flush = True
                return

        self._sections.append(make_section())
        self._need_flush = True

    def __delitem__(self, key: str) -> None:
        self._check_closed()

        found = None
        for i, item in enumerate(self._sections):
            if item.name == key:
                found = i
                break

        if found is None:
            raise SectionNotFound("MultiCSVFile does not "
                                  f"have section named {key!r}.")
        else:
            del self._sections[found]
            self._need_flush = True

    def __iter__(self) -> Iterator[str]:
        self._check_closed()

        for section in self._sections:
            yield section.name

    def __len__(self) -> int:
        return len(self._sections)

    def __contains__(self, key: object) -> bool:
        self._check_closed()

        for item in self._sections:
            if item.name == key:
                return True

        return False

    def section(self, name: str) -> TextIO:
        if name not in self:
            self[name] = io.StringIO("")

        return self[name]

    def close(self) -> None:
        if not self._closed:
            try:
                self.flush()
            finally:
                if self._own_file:
                    try:
                        self._file.close()
                    finally:
                        self._closed = True
                else:
                    self._closed = True

    def _write_file(self) -> None:
        # Collect all section text BEFORE touching the base file.  Each
        # descriptor is a TextIOWrapper over a SubBinaryIO that reads directly
        # from `self._file`; once we seek(0) + truncate() below those bytes
        # would be gone.  Pre-reading here makes the subsequent rewrite safe.
        sections_data: List[tuple[str, str]] = []
        for section in self._sections:
            saved_pos = section.descriptor.tell()
            try:
                section.descriptor.seek(0)
                text: str = section.descriptor.read()
            finally:
                section.descriptor.seek(saved_pos)
            sections_data.append((section.name, text))

        self._file.seek(0)
        self._file.truncate()

        for name, text in sections_data:
            self._file.write(f"[{name}]\n".encode(self._encoding))
            self._file.write(text.encode(self._encoding))

    def flush(self) -> None:
        if self._file.closed:
            raise CSVFileBaseIOClosed("Base file is closed in flush.")

        if not self._need_flush:
            return

        saved = self._file.tell()
        try:
            self._write_file()
            self._need_flush = False
        finally:
            self._file.seek(saved)

    def __enter__(self) -> 'MultiCSVFile':
        return self

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[object]) -> None:
        self.close()

    def _initialize_sections_wrapped(self) -> None:
        # Binary readline() gives exact byte offsets from tell() with no
        # opaque codec-state cookies, but only when the encoding maps \n to
        # the single byte 0x0a.  EBCDIC encodings use 0x25 for \n, and
        # UTF-16/32 encode \n as a multi-byte sequence; in those cases we
        # fall back to a whole-file text-decode approach.
        try:
            newline_byte = '\n'.encode(self._encoding)
        except (LookupError, UnicodeEncodeError):
            newline_byte = b'\n'

        if newline_byte == b'\n':
            self._initialize_sections_binary()
        else:
            self._initialize_sections_text()

    def _initialize_sections_binary(self) -> None:
        """Section detection via binary readline + byte-offset SubBinaryIO."""
        self._file.seek(0)
        current_section: Optional[str] = None
        section_start = 0  # byte offset where current section's data begins

        while True:
            line_start: int = self._file.tell()
            line_bytes: bytes = self._file.readline()

            if not line_bytes:
                # EOF – close out the last section.
                if current_section is not None:
                    self._sections.append(MultiCSVSection(
                        name=current_section,
                        descriptor=io.TextIOWrapper(
                            SubBinaryIO(self._file, section_start, line_start),
                            encoding=self._encoding,
                        ),
                    ))
                break

            line_text = line_bytes.decode(self._encoding,
                                          errors='replace').strip()
            if line_text:
                row = next(csv.reader([line_text]))
                if len(row) == 0:
                    break

                first = row[0].strip()
                rest = row[1:]

                if first.startswith("[") and \
                   first.endswith("]") and \
                   all(not x for x in rest):

                    # Close the previous section (data ran from
                    # section_start up to – but not including – this
                    # header line).
                    if current_section is not None:
                        self._sections.append(MultiCSVSection(
                            name=current_section,
                            descriptor=io.TextIOWrapper(
                                SubBinaryIO(self._file,
                                            section_start, line_start),
                                encoding=self._encoding,
                            ),
                        ))
                    current_section = first[1:-1]
                    # Section data starts right after the header line.
                    section_start = self._file.tell()

    def _initialize_sections_text(self) -> None:
        """Fallback for encodings whose newline is not the single byte 0x0a
        (EBCDIC, UTF-16, UTF-32, …).  Wraps the file in a TextIOWrapper to
        iterate line by line without loading everything into memory at once,
        then stores each section as an io.StringIO.

        TextIOWrapper is detached (not closed) at the end so that *self._file*
        remains open for subsequent operations.
        """
        self._file.seek(0)
        wrapper = io.TextIOWrapper(
            self._file,
            encoding=self._encoding,
            errors='replace',
            line_buffering=False,
        )
        try:
            current_section: Optional[str] = None
            section_lines: List[str] = []

            for line in wrapper:
                stripped = line.strip()
                if stripped:
                    row = next(csv.reader([stripped]))
                    if len(row) == 0:
                        break

                    first = row[0].strip()
                    rest = row[1:]

                    if first.startswith("[") and \
                       first.endswith("]") and \
                       all(not x for x in rest):

                        if current_section is not None:
                            self._sections.append(MultiCSVSection(
                                name=current_section,
                                descriptor=io.StringIO(
                                    "".join(section_lines)),
                            ))
                        current_section = first[1:-1]
                        section_lines = []
                        continue

                if current_section is not None:
                    section_lines.append(line)

            if current_section is not None:
                self._sections.append(MultiCSVSection(
                    name=current_section,
                    descriptor=io.StringIO("".join(section_lines)),
                ))
        finally:
            wrapper.detach()  # release self._file without closing it

    def _initialize_sections(self) -> None:
        if not self._file.readable():
            return

        saved = self._file.tell()
        try:
            self._initialize_sections_wrapped()
        finally:
            self._file.seek(saved)

    def _check_closed(self) -> None:
        if self._closed:
            raise OpOnClosedCSVFileError("I/O operation on closed file.")

    def __del__(self) -> None:
        if self._initialized:
            try:
                self.close()
            except CSVFileBaseIOClosed:
                pass
