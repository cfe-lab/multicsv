
from typing import TextIO, Optional, Type, List, MutableMapping, Iterator
import shutil
import os
import io
from .subtextio import SubTextIO
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
    - The class initializes by reading the CSV file and identifying sections
    encapsulated within bracketed headers (e.g., [section_name]).
    - Each section is represented by a MultiCSVSection that holds a
    descriptor to a SubTextIO object, allowing isolated operations
    within that section.
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
    from multicsv.multicsvfile import MultiCSVFile

    # Initialize the MultiCSVFile with a base CSV string
    csv_content = io.StringIO("[section1]\na,b,c\n1,2,3\n"
                              "[section2]\nd,e,f\n4,5,6\n")
    csv_file = MultiCSVFile(csv_content)

    # Accessing a section
    section1 = csv_file["section1"]
    print(section1.read())  # Should output 'a,b,c\n1,2,3\n'

    # Adding a new section
    new_section = io.StringIO("g,h,i\n7,8,9\n")
    csv_file["section3"] = new_section
    csv_file.flush()

    # Verify the new section is added
    csv_content.seek(0)
    print(csv_content.read())
    # Outputs
    # [section1]
    # a,b,c
    # 1,2,3
    # [section2]
    # d,e,f
    # 4,5,6
    # [section3]
    # g,h,i
    # 7,8,9
    ```

    Caveats:
    --------
    - Writing to and reading from the base TextIO when it is used in
    MultiCSVFile can lead to unexpected results.
    - Always ensure to call `flush` or use context management to commit changes
    back to the base CSV file.
    - Mixing reading/writing operations from MultiCSVFile and the base TextIO
    directly may cause inconsistencies.
    """

    def __init__(self, file: TextIO, own: bool = False):
        self._initialized = False
        self._need_flush = False
        self._own_file = own
        self._file = file
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
            del self._sections[i]
            self._need_flush = True

    def __iter__(self) -> Iterator[str]:
        self._check_closed()

        return iter(map(lambda x: x.name, self._sections))

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

    def _write_section(self, section: MultiCSVSection) -> None:
        self._file.write(f"[{section.name}]\n")

        initial_section_pos = section.descriptor.tell()
        try:
            section.descriptor.seek(0)
            shutil.copyfileobj(section.descriptor, self._file)
        finally:
            section.descriptor.seek(initial_section_pos)

    def _write_file(self) -> None:
        self._file.seek(0)
        self._file.truncate()

        for section in self._sections:
            self._write_section(section)

    def flush(self) -> None:
        if self._file.closed:
            raise CSVFileBaseIOClosed("Base file is closed in flush.")

        if not self._need_flush:
            return

        initial_file_pos = self._file.tell()
        try:
            self._write_file()
            self._need_flush = False
        finally:
            self._file.seek(initial_file_pos)

    def __enter__(self) -> 'MultiCSVFile':
        return self

    def __exit__(self,
                 exc_type: Optional[Type[BaseException]],
                 exc_val: Optional[BaseException],
                 exc_tb: Optional[object]) -> None:
        self.close()

    def _initialize_sections_wrapped(self) -> None:
        current_section: Optional[str] = None
        section_start = 0
        previous_position = 0

        def end_section() -> None:
            if current_section is not None:
                descriptor = SubTextIO(self._file,
                                       start=section_start,
                                       end=previous_position)
                section = MultiCSVSection(name=current_section,
                                          descriptor=descriptor)
                self._sections.append(section)

        self._file.seek(0, os.SEEK_END)
        final_position = self._file.tell()
        if final_position == 0:
            return

        self._file.seek(0)
        while True:
            line = self._file.readline()
            if not line:
                break

            current_position = previous_position + len(line)

            if line.endswith("\n"):
                line = line[:-1]

            row = line.split(",")

            if row:
                first = row[0].strip()
                rest = row[1:]

                if first.startswith("[") and \
                   first.endswith("]") and \
                   all(not x for x in rest):

                    end_section()
                    current_section = first[1:-1]
                    section_start = current_position

            previous_position = current_position

        end_section()

    def _initialize_sections(self) -> None:
        initial_file_pos = self._file.tell()
        try:
            self._initialize_sections_wrapped()
        finally:
            self._file.seek(initial_file_pos)

    def _check_closed(self) -> None:
        """
        Helper method to verify if the IO object is closed.
        """

        if self._closed:
            raise OpOnClosedCSVFileError("I/O operation on closed file.")

    def __del__(self) -> None:
        if self._initialized:
            try:
                self.close()
            except CSVFileBaseIOClosed:
                pass
