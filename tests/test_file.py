import io
import pytest
from typing import TextIO
from multicsv.file import MultiCSVFile
from multicsv.exceptions import SectionNotFound, CSVFileBaseIOClosed


@pytest.fixture
def simple_csv() -> TextIO:
    content = """\
[section1]
a,b,c
1,2,3
[section2]
d,e,f
4,5,6
"""
    return io.StringIO(content)


@pytest.fixture
def empty_csv() -> TextIO:
    return io.StringIO("")


@pytest.fixture
def no_section_csv() -> TextIO:
    content = """\
a,b,c
1,2,3
d,e,f
4,5,6
"""
    return io.StringIO(content)


def test_read_section(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    section1 = csv_file["section1"]
    assert section1.read() == "a,b,c\n1,2,3\n"

    section2 = csv_file["section2"]
    assert section2.read() == "d,e,f\n4,5,6\n"


def test_write_section(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    section3 = io.StringIO("g,h,i\n7,8,9\n")
    csv_file["section3"] = section3

    csv_file.flush()
    simple_csv.seek(0)
    assert simple_csv.read() == "[section1]\na,b,c\n1,2,3\n[section2]\nd,e,f\n4,5,6\n[section3]\ng,h,i\n7,8,9\n"


def test_delete_section(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    del csv_file["section1"]

    csv_file.flush()
    simple_csv.seek(0)
    assert simple_csv.read() == "[section2]\nd,e,f\n4,5,6\n"


def test_iterate_sections(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    sections = list(iter(csv_file))
    assert sections == ["section1", "section2"]


def test_getitem_not_found(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    with pytest.raises(SectionNotFound):
        _ = csv_file["section3"]


def test_contains(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    assert "section1" in csv_file
    assert "section2" in csv_file
    assert "section3" not in csv_file


def test_len(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    assert len(csv_file) == 2


def test_close(simple_csv):
    csv_file = MultiCSVFile(simple_csv)

    simple_csv.close()
    assert simple_csv.closed is True

    with pytest.raises(CSVFileBaseIOClosed):
        csv_file.flush()


def test_context_manager(simple_csv):
    with MultiCSVFile(simple_csv) as csv_file:
        assert len(csv_file) == 2

    assert csv_file._closed is True


def test_flush_on_closed_file(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    csv_file.close()
    csv_file.flush()


def test_initialize_sections_on_empty_file(empty_csv):
    csv_file = MultiCSVFile(empty_csv)
    assert len(csv_file) == 0


def test_initialize_sections_on_no_section_file(no_section_csv):
    csv_file = MultiCSVFile(no_section_csv)
    assert len(csv_file) == 0  # No sections should be found


def test_update_existing_section(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    new_section = io.StringIO("new,data\n")
    csv_file["section1"] = new_section

    csv_file.flush()
    simple_csv.seek(0)
    expected_content = "[section1]\nnew,data\n[section2]\nd,e,f\n4,5,6\n"
    assert simple_csv.read() == expected_content


def test_del_non_existent_section(simple_csv):
    csv_file = MultiCSVFile(simple_csv)
    with pytest.raises(SectionNotFound):
        del csv_file["section9"]


def test_multiple_writes_with_flush(simple_csv):
    csv_file = MultiCSVFile(simple_csv)

    section3 = io.StringIO("x,y,z\n10,11,12\n")
    csv_file["section3"] = section3
    csv_file.flush()

    section4 = io.StringIO("p,q,r\n13,14,15\n")
    csv_file["section4"] = section4
    csv_file.flush()

    simple_csv.seek(0)
    expected_content = "[section1]\na,b,c\n1,2,3\n[section2]\nd,e,f\n4,5,6\n[section3]\nx,y,z\n10,11,12\n[section4]\np,q,r\n13,14,15\n"
    assert simple_csv.read() == expected_content


def test_reading_after_writing(simple_csv):
    csv_file = MultiCSVFile(simple_csv)

    section3 = io.StringIO("x,y,z\n10,11,12\n")
    csv_file["section3"] = section3
    csv_file.flush()

    section = csv_file["section3"]
    section.seek(0)
    assert section.read() == "x,y,z\n10,11,12\n"


def test_iterates_zero_length_multicsvfile(empty_csv):
    csv_file = MultiCSVFile(empty_csv)
    assert list(iter(csv_file)) == []


def test_section_not_found_for_deleted_section(simple_csv):
    csv_file = MultiCSVFile(simple_csv)

    assert csv_file["section1"]
    del csv_file["section1"]

    with pytest.raises(SectionNotFound):
        csv_file["section1"]


@pytest.mark.parametrize("initial_content, expected_sections", [
    ("[first_section]\na,b,c\n1,2,3\n[second_section]\nd,e,f\n4,5,6\n",
     ["first_section", "second_section"]),
    ("", []),
    ("[lonely_section]\ng,h,i\n7,8,9\n", ["lonely_section"]),
])
def test_various_initial_contents(initial_content, expected_sections):
    file = io.StringIO(initial_content)
    csv_file = MultiCSVFile(file)
    assert list(iter(csv_file)) == expected_sections
