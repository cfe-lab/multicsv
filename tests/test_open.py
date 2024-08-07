
import pytest
import io
from multicsv.open import multicsv_open

simple_csv_content = """\
[section1]
a,b,c
1,2,3
[section2]
d,e,f
4,5,6
"""


def test_open_read(tmp_path):
    path = tmp_path / "file1.txt"
    initial_content = simple_csv_content

    # Write initial content to the temp file
    with open(path, "w") as writer:
        writer.write(initial_content)

    # Validate correct write and read operations on the file
    with open(path, "r") as file:
        assert file.read() == initial_content

    # Using multicsv_open to read sections from the file
    with multicsv_open(path) as csv_file:
        section1 = csv_file["section1"]

        # Validate content of section1
        assert section1.read() == "a,b,c\n1,2,3\n"
        assert section1.read() == ""  # Ensure next read is empty as file is read completely

        section2 = csv_file["section2"]

        # Validate content of section2
        assert section2.read() == "d,e,f\n4,5,6\n"
        assert section2.read() == ""  # Ensure next read is empty as file is read completely

        # Validate section names
        assert list(csv_file) == ['section1', 'section2']

    # Validate final content is unchanged
    with open(path, "r") as file:
        assert file.read() == initial_content


# Additional test cases to cover more scenarios
def test_open_write(tmp_path):
    path = tmp_path / "file2.txt"

    # Writing sections using multicsv_open
    with multicsv_open(path, "wt") as csv_file:
        csv_file["section1"] = io.StringIO("a,b,c\n1,2,3\n")
        csv_file["section2"] = io.StringIO("d,e,f\n4,5,6\n")
        # csv_file.flush()

    # Validate the written content
    with open(path, "r") as file:
        expected_content = simple_csv_content
        # expected_content = "xxx"
        assert expected_content == file.read()


def test_open_append(tmp_path):
    path = tmp_path / "file3.txt"

    initial_content = """\
[section1]
a,b,c
1,2,3
"""

    with open(path, "w") as writer:
        writer.write(initial_content)

    # Appending new sections using multicsv_open
    with multicsv_open(path, "a+t") as csv_file:
        csv_file["section2"] = io.StringIO("d,e,f\n4,5,6\n")

    # Validate the appended content
    with open(path, "r") as file:
        expected_content = initial_content + "[section2]\nd,e,f\n4,5,6\n"
        assert file.read() == expected_content
