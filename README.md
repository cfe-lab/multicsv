
# MultiCSV

[![codecov](https://codecov.io/gh/cfe-lab/multicsv/branch/master/graph/badge.svg)](https://codecov.io/gh/cfe-lab/multicsv)
[![types - Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://github.com/python/mypy)
[![flake8 checked](https://img.shields.io/badge/flake8-checked-blueviolet.svg)](https://github.com/PyCQA/flake8)
[![License - GPL3](https://img.shields.io/badge/license-GPLv3-blue)](https://spdx.org/licenses/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/cfe-lab/multicsv/pulls)

Python library `multicsv` is designed for handling multi-CSV format
files. It provides an interface for reading, writing, and manipulating
sections of a CSV file as individual text file objects.

### Key Features

- **Efficient Section Management:** Read and write multiple
  independent sections within a single CSV file.
- **TextIO Interface:** Sections are treated as TextIO objects,
  enabling familiar file operations.
- **Flexible Operations:** Supports reading, writing, iterating, and
  deleting sections.
- **Context Management:** Ensures resource safety with `with`
  statement compatibility.
- **Integrated Testing:** Includes comprehensive unit tests, covering
  100% of the functionality.

## The Multi-CSV Format

The multi-CSV format is an extension of the traditional CSV
(Comma-Separated Values) format that supports dividing a single file
into multiple independent sections. Each section is demarcated by a
header enclosed in square brackets, e.g., `[section_name]`.
This format is commonly known for usage in Illumina-MiSeq sample sheet
files.

Conceptually, this file format provides the ability to store a whole
SQL database in a single, human readable file.

### Example

Here's a simplified example of a multi-CSV file:

```csv
[section1]
header1,header2,header3
value1,value2,value3

[section2]
headerA,headerB,headerC
valueA,valueB,valueC
```

In the example above, the file contains two sections: `section1` and
`section2`. Each section has its own headers and rows of data.

## Usage

Here's a quick example of how to use the `multicsv` library:

```python
import csv
import multicsv

with multicsv.open('example.csv', mode='w+') as csv_file:
    # Write the CSV content to the file
    csv_file.section('section1').write("header1,header2,header3\nvalue1,value2,value3\n")
    csv_file.section('section2').write("header4,header5,header6\nvalue4,value5,value6\n")

    # Read a section using the csv module
    csv_reader = csv.reader(csv_file['section1'])
    assert list(csv_reader) == [['header1', 'header2', 'header3'],
                                ['value1', 'value2', 'value3']]
```

There are only two methods exported in `multicsv`: `open` and `wrap`.
This is how the latter one is meant to be used:

```python
import io
import multicsv

# Initialize the MultiCSVFile with a base CSV string
csv_content = io.StringIO("""\
[section1]
a,b,c
1,2,3
[section2]
d,e,f
4,5,6
""")

csv_file = multicsv.wrap(csv_content)

# Accessing a section
section1 = csv_file["section1"]
print(section1.read())  # Outputs: "a,b,c\n1,2,3\n"

# Adding a new section
new_section = io.StringIO("g,h,i\n7,8,9\n")
csv_file["section3"] = new_section
csv_file.flush()

# Verify the new section is added
csv_content.seek(0)
print(csv_content.read())
# Outputs:
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

Both exported methods return a `MultiCSVFile` object.
Objects of that class are `MutableMapping`s from names of sections (`: str`) to contents of sections (`: TextIO`).

So, for instance, this is how to print all sections in a multi-csv file:

```python
import multicsv

for section in multicsv.open("example.csv"):
    print(section)
```

## Installation

Install the library using pip:

```bash
pip install multicsv
```

## Development

### Setting Up

Set up your environment for development as follows:

1. Clone the repository:

    ```bash
    git clone https://github.com/cfe-lab/multicsv.git
    ```

2. Navigate to the project directory:

    ```bash
    cd multicsv
    ```

3. Create a virtual environment:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4. Install dependencies:

    ```bash
    pip install -e .[dev,test]
    ```

### Running Tests

Run the test suite to ensure everything is functioning correctly:

```bash
pytest
```

## Contributing

Contributions are welcome! Please follow these steps for contributions:

1. Fork the repository.
2. Create a new branch with a descriptive name.
3. Make your changes and ensure the test suite passes.
4. Open a pull request with a clear description of what you've done.

## License

This project is licensed under the GPL-3.0 License - see the
[LICENSE](COPYING) file for details.
