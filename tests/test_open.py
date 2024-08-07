
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

    with open(path, "w") as writer:
        writer.write(initial_content)

    with open(path, "r") as file:
        assert file.read() == initial_content

    with open(path, "r") as file:
        assert file.read() == initial_content

    with multicsv_open(path) as file:
        data1 = file["section1"]
        assert """\
a,b,c
1,2,3
""" == data1.read()

        assert "" == data1.read()

        data2 = file["section2"]
        assert """\
d,e,f
4,5,6
""" == data2.read()

        assert "" == data2.read()

        assert ['section1', 'section2'] == list(file)

    with open(path, "r") as file:
        assert file.read() == initial_content
