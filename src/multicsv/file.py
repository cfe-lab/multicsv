
import csv
from typing import TextIO, Optional, Type, List, MutableMapping, Iterator
import shutil
from .subtextio import SubTextIO
from .exceptions import OpOnClosedCSVFileError, CSVFileBaseIOClosed, \
    SectionNotFound
from .section import MultiCSVSection


class MultiCSVFile(MutableMapping[str, TextIO]):
    def __init__(self, file: TextIO):
        self._initialized = False
        self._file = file
        self._closed = self._file.closed
        self._sections: List[MultiCSVSection] = []
        self._initialize_sections()
        self._initialized = True

    def __getitem__(self, key: str) -> TextIO:
        for item in self._sections:
            if item.name == key:
                return item.descriptor

        raise SectionNotFound("MultiCSVFile does not "
                              f"have section named {key!r}.")

    def __setitem__(self, key: str, value: TextIO) -> None:
        def make_section() -> MultiCSVSection:
            return MultiCSVSection(name=key, descriptor=value)

        for i, item in enumerate(self._sections):
            if item.name == key:
                self._sections[i] = make_section()
                return

        self._sections.append(make_section())

    def __delitem__(self, key: str) -> None:
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

    def __iter__(self) -> Iterator[str]:
        return iter(map(lambda x: x.name, self._sections))

    def __len__(self) -> int:
        return len(self._sections)

    def __contains__(self, key: object) -> bool:
        for item in self._sections:
            if item.name == key:
                return True
        return False

    def close(self) -> None:
        if not self._closed:
            try:
                self.flush()
            finally:
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

        if self._closed:
            return

        initial_file_pos = self._file.tell()
        try:
            self._write_file()
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
        reader = csv.reader(self._file)

        current_section: Optional[str] = None
        section_start = 0
        previous_position = 0

        self._file.seek(0)

        def end_section() -> None:
            if current_section is not None:
                descriptor = SubTextIO(self._file,
                                       start=section_start,
                                       end=previous_position)
                section = MultiCSVSection(name=current_section,
                                          descriptor=descriptor)
                self._sections.append(section)

        for row in reader:
            current_position = self._file.tell()
            if row:

                first = row[0]
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
