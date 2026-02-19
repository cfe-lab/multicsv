from typing import BinaryIO, TextIO, Optional, Type, List, MutableMapping, Iterator
import csv
import io
import os
from .subbinaryio import SubBinaryIO
from .exceptions import OpOnClosedCSVFileError, CSVFileBaseIOClosed, SectionNotFound
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

    def __init__(
        self, file: BinaryIO, own: bool = False, encoding: str = "utf-8"
    ) -> None:
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

        raise SectionNotFound(f"MultiCSVFile does not have section named {key!r}.")

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
            raise SectionNotFound(f"MultiCSVFile does not have section named {key!r}.")
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
        # descriptor reads directly from `self._file`; once we truncate below
        # those bytes would be gone.  Pre-reading makes the subsequent rewrite safe.
        sections_data: List[tuple[str, str]] = []  # (name, text) pairs
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

        # Write through a TextIOWrapper so the BOM (for utf-16, utf-32,
        # utf-8-sig) is emitted exactly once at the start of the file rather
        # than once per section.  flush() + detach() commit the buffer without
        # closing self._file.
        write_wrapper = io.TextIOWrapper(
            self._file,
            encoding=self._encoding,
            line_buffering=False,
        )
        try:
            for name, text in sections_data:
                write_wrapper.write(f"[{name}]\n")
                write_wrapper.write(text)
            write_wrapper.flush()
        finally:
            write_wrapper.detach()  # release self._file without closing it

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

    def __enter__(self) -> "MultiCSVFile":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        self.close()

    def _resolved_section_encoding(self) -> str:
        """Return a BOM-free encoding variant for section ``TextIOWrapper``\\s.

        BOM-aware codec names (``utf-16``, ``utf-32``, ``utf-8-sig``) require
        a BOM at the very first byte of the stream they wrap.  Section byte
        ranges start *after* the file-level BOM, so wrapping a
        ``SubBinaryIO(file, section_start, section_end)`` with one of those
        codecs raises ``UnicodeError: stream does not start with BOM``.

        This method reads the first four bytes of the file once to identify
        the byte-order mark actually present, and returns the corresponding
        BOM-free variant (e.g. ``utf-16-le``, ``utf-32-be``, ``utf-8``).
        For encodings that never use a BOM the original ``self._encoding`` is
        returned unchanged.
        """
        saved = self._file.tell()
        try:
            bom = self._file.read(4)
        finally:
            self._file.seek(saved)
        # Check utf-32 before utf-16: the UTF-32-LE BOM (\xff\xfe\x00\x00)
        # starts with the same two bytes as the UTF-16-LE BOM.
        if bom[:4] == b'\xff\xfe\x00\x00':
            return 'utf-32-le'
        if bom[:4] == b'\x00\x00\xfe\xff':
            return 'utf-32-be'
        if bom[:2] == b'\xff\xfe':
            return 'utf-16-le'
        if bom[:2] == b'\xfe\xff':
            return 'utf-16-be'
        if bom[:3] == b'\xef\xbb\xbf':
            return 'utf-8'
        return self._encoding

    def _initialize_sections_wrapped(self) -> None:
        """Scan the file in text mode to locate section headers, then create
        each section's descriptor as a plain ``TextIOWrapper`` over a
        ``SubBinaryIO(file, section_start, section_end)`` with the correct
        byte boundaries.  No section content is loaded into memory during
        initialisation.

        **How byte offsets are obtained from text-mode scanning**

        ``TextIOWrapper.tell()`` returns an opaque cookie, not a raw byte
        offset.  However ``TextIOWrapper.seek(cookie)`` calls
        ``buffer.seek(raw_byte_offset)`` internally, which advances the
        underlying ``SubBinaryIO`` (``sub``) to the exact byte position
        encoded in the cookie.  Reading ``sub.tell()`` afterwards gives the
        plain integer boundary needed to create section ``SubBinaryIO``
        objects::

            cookie = wrapper.tell()
            wrapper.seek(cookie)    # sub is now at the right byte position
            byte_pos = sub.tell()   # plain integer — always correct

        This works for every encoding, including stateful codecs.

        **Why section wrappers use a BOM-free encoding**

        Section data does not start at byte 0 of the file, so the file-level
        BOM is not present in the section's byte range.
        ``_resolved_section_encoding()`` reads the BOM once and returns the
        appropriate byte-order-specific variant (``utf-16-le``, etc.) so that
        each section ``TextIOWrapper`` starts reading without expecting a BOM.
        """
        self._file.seek(0, os.SEEK_END)
        file_size = self._file.tell()
        self._file.seek(0)

        section_enc = self._resolved_section_encoding()

        sub = SubBinaryIO(self._file, 0, file_size)
        wrapper = io.TextIOWrapper(sub, encoding=self._encoding, errors='replace')

        def byte_offset() -> int:
            """Return sub's current byte position, synced from wrapper."""
            cookie = wrapper.tell()
            wrapper.seek(cookie)
            return sub.tell()

        try:
            current_section: Optional[str] = None
            section_start = 0

            while True:
                line_start = byte_offset()
                line = wrapper.readline()

                if not line:
                    # EOF – close out the last open section.
                    if current_section is not None:
                        self._sections.append(MultiCSVSection(
                            name=current_section,
                            descriptor=io.TextIOWrapper(
                                SubBinaryIO(self._file, section_start, line_start),
                                encoding=section_enc,
                            ),
                        ))
                    break

                stripped = line.strip()
                if stripped:
                    row = next(csv.reader([stripped]))
                    if len(row) == 0:
                        break

                    first = row[0].strip()
                    rest = row[1:]

                    if (
                        first.startswith('[')
                        and first.endswith(']')
                        and all(not x for x in rest)
                    ):
                        # Close the previous section.
                        if current_section is not None:
                            self._sections.append(MultiCSVSection(
                                name=current_section,
                                descriptor=io.TextIOWrapper(
                                    SubBinaryIO(self._file, section_start, line_start),
                                    encoding=section_enc,
                                ),
                            ))
                        current_section = first[1:-1]
                        # Section data starts right after this header line.
                        section_start = byte_offset()
        finally:
            wrapper.detach()  # release sub / self._file without closing them

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
