
from pathlib import Path
import pytest
import io
import csv

import multicsv


@pytest.fixture
def example_file(tmp_path: Path) -> Path:
    path = tmp_path / "file1.txt"
    content = """\
[section1]
a,b,c
1,2,3
[section2]
d,e,f
4,5,6
"""

    with open(path, "w") as writer:
        writer.write(content)

    return path


def test_readlines(example_file: Path) -> None:
    with multicsv.open(example_file) as mapping:
        section1 = mapping["section2"].readlines()
        assert section1 == ['d,e,f\n', '4,5,6\n']


def test_read_csv(example_file: Path) -> None:
    import csv

    with multicsv.open(example_file) as mapping:
        section1_file = mapping["section2"]
        section1_csv = csv.reader(section1_file)
        section1 = list(section1_csv)

        assert section1 == [['d', 'e', 'f'],
                            ['4', '5', '6']]


def test_write_csv(example_file):
    with multicsv.open(example_file, mode='w+') as csv_file:
        # Write the CSV content to the file
        csv_file['section1'] = io.StringIO("header1,header2,header3\nvalue1,value2,value3\n")
        csv_file['section2'] = io.StringIO("header4,header5,header6\nvalue4,value5,value6\n")

        # Read a section using the csv module
        section1 = csv_file['section1']
        csv_reader = csv.reader(section1)
        assert list(csv_reader) == [['header1', 'header2', 'header3'],
                                    ['value1', 'value2', 'value3']]

        # Get all sections:
        all_sections = list(csv_file)
        assert ['section1', 'section2'] == all_sections


def test_open_csv():
    # Initialize the MultiCSVFile with a base CSV string
    csv_content = io.StringIO("[section1]\na,b,c\n1,2,3\n[section2]\nd,e,f\n4,5,6\n")
    csv_file = multicsv.wrap(csv_content)

    # Accessing a section
    section1 = csv_file["section1"]
    assert section1.read() == "a,b,c\n1,2,3\n"

    # Adding a new section
    new_section = io.StringIO("g,h,i\n7,8,9\n")
    csv_file["section3"] = new_section
    csv_file.flush()

    # Verify the new section is added
    csv_content.seek(0)
    assert csv_content.read() == """\
[section1]
a,b,c
1,2,3
[section2]
d,e,f
4,5,6
[section3]
g,h,i
7,8,9
"""
