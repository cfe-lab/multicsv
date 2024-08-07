
from pathlib import Path
import pytest

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
