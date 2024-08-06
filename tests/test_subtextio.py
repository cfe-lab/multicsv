
import io
from typing import TextIO
import pytest
import os
from multicsv.subtextio import SubTextIO

@pytest.fixture
def base_textio() -> TextIO:
    return io.StringIO("""\
Hello World,
this is a
test
""")

@pytest.fixture
def large_textio() -> TextIO:
    content = "a" * 10000 + "0123456789\n" + "a" * 5000 + "Python is Great\n" + "a" * 10000
    return io.StringIO(content)

def test_read_1(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=15)
    assert sub_text.read() == "World,\nth"
    assert sub_text.read() == ""
    assert sub_text.read() == ""
    assert sub_text.read() == ""

def test_read_2(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.read() == "World,\nthis is "
    assert sub_text.read() == ""
    assert sub_text.read() == ""
    assert sub_text.read() == ""

def test_readline_1(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=15)
    assert sub_text.readline() == "World,\n"
    assert sub_text.readline() == "th"
    assert sub_text.readline() == ""  # Ensure end of the segment is reached
    assert sub_text.readline() == ""  # Ensure end of the segment is reached
    assert sub_text.readline() == ""  # Ensure end of the segment is reached

def test_readline_2(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.readline() == "World,\n"
    assert sub_text.readline() == "this is "
    assert sub_text.readline() == ""  # Ensure end of the segment is reached
    assert sub_text.readline() == ""  # Ensure end of the segment is reached
    assert sub_text.readline() == ""  # Ensure end of the segment is reached

def test_readlines(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.readlines() == ["World,\n", "this is "]

def test_write(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.write("NewContent")
    sub_text.seek(0)
    assert sub_text.read() == "NewContents is "

    sub_text.flush()
    base_textio.seek(0)
    assert base_textio.read() == "Hello NewContents is a\ntest\n"

def test_write_past_end(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    longstring = 'NewContent' * 20
    sub_text.write(longstring)
    sub_text.seek(0)
    assert sub_text.read() == longstring

    sub_text.flush()
    base_textio.seek(0)
    assert base_textio.read() == f"Hello {longstring}a\ntest\n"

def test_writelines(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.writelines(["Line1\n", "Line2\n"])
    sub_text.seek(0)
    assert sub_text.read() == "Line1\nLine2\nis "

def test_truncate(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.truncate()
    sub_text.write("CleanSlate")
    sub_text.seek(0)
    assert sub_text.read() == "CleanSlate"

def test_truncate_with_arg(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.truncate(4)
    assert sub_text.read() == "Worl"
    sub_text.flush()

    base_textio.seek(0)
    assert base_textio.read() == """\
Hello Worla
test
 is a
test
"""

def test_truncate_past_end(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.truncate(999)
    assert base_textio.read() == """\
a
test
"""
    assert sub_text.length == 15 == 21 - 6

def test_seek_tell(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.seek(5)
    assert sub_text.tell() == 5
    assert sub_text.read() == ",\nthis is "

def test_flush(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.write("Overwritten")
    sub_text.flush()
    base_textio.seek(0)
    assert base_textio.read() == "Hello Overwritten is a\ntest\n"

def test_iter(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    lines = list(sub_text)
    assert lines == ["World,\n", "this is "]

def test_context_manager(base_textio):
    with SubTextIO(base_textio, start=6, end=21) as sub_text:
        sub_text.write("ContextWrite")
        sub_text.seek(0)
        assert sub_text.read() == "ContextWriteis "
    base_textio.seek(0)
    assert base_textio.read() == "Hello ContextWriteis a\ntest\n"

# Edge case for empty subsections
def test_empty_section(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=6)
    assert sub_text.read() == ""
    assert sub_text.readline() == ""
    assert sub_text.readlines() == []
    assert sub_text.tell() == 0

# Test for large buffer
def test_large_buffer(large_textio):
    sub_text = SubTextIO(large_textio, start=10000, end=20000)
    sub_text.seek(9999)
    assert sub_text.tell() == 9999
    sub_text.seek(0)
    assert sub_text.read(5) == "01234"
    sub_text.seek(5, os.SEEK_CUR)
    sub_text.seek(1, os.SEEK_CUR)
    sub_text.seek(5000, os.SEEK_CUR)
    assert sub_text.readline() == "Python is Great\n"

# Test long text write
def test_long_write(base_textio):
    long_text = "x" * 1000
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.write(long_text)
    sub_text.seek(0)
    assert sub_text.read(len(long_text)) == long_text

# Test seek and read after close
def test_operations_after_close(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.close()
    with pytest.raises(ValueError):
        sub_text.read()
    with pytest.raises(ValueError):
        sub_text.write("Test")
    with pytest.raises(ValueError):
        sub_text.seek(1)

# Test unexpected `whence` value in `seek`
def test_invalid_seek_whence(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    with pytest.raises(ValueError):
        sub_text.seek(0, whence=3)

# Test `flush` without any open/close
def test_flush_without_open_close(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.write("FlushTest")
    sub_text.flush()
    base_textio.seek(0)
    assert base_textio.read() == "Hello FlushTestis is a\ntest\n"

# Test read after delete
def test_read_after_truncate(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.truncate()
    assert sub_text.read() == ""

# Test write after delete
def test_write_truncate(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.truncate()
    assert sub_text.read() == ""
    sub_text.write("AfterDelete")
    sub_text.seek(0)
    assert sub_text.read() == "AfterDelete"

# Test multiple writes without flushing
def test_multiple_writes(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.write("First")
    sub_text.write("Second")
    sub_text.seek(0)
    assert sub_text.read() == "FirstSecond is "

# Test read and write interleaving
def test_read_write_interleaving(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.write("Interleave")
    sub_text.seek(0)
    assert sub_text.read(5) == "Inter"
    sub_text.write("Change")
    sub_text.seek(0)
    assert sub_text.read() == "InterChange is "

# Test context management with exception
def test_context_manager_with_exception(base_textio):
    try:
        with SubTextIO(base_textio, start=6, end=21) as sub_text:
            sub_text.write("ExceptionTest")
            raise IndexError("Testing Exception")
    except IndexError:
        base_textio.seek(0)
        assert 'Hello ExceptionTests a\ntest\n' == base_textio.read()

# Test `seek` past the end of buffer
def test_seek_past_end(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=15)
    sub_text.seek(20)
    assert sub_text.tell() == 9

# Test `read` with exact buffer end condition
def test_read_exact_buffer_end(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=15)
    assert sub_text.read(size=9) == "World,\nth"

# Test `read` after flushing and re-seeking
def test_read_after_flush_and_seek(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.write("AfterFlush")
    sub_text.flush()
    sub_text.seek(0)
    assert sub_text.read() == "AfterFlushs is "

# Test `close` without `flush`
def test_close_without_flush(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    sub_text.write("CloseWithoutFlush")
    sub_text.close()
    base_textio.seek(0)
    assert base_textio.read() == "Hello CloseWithoutFlusha\ntest\n"

def test_iterate(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    actual_lines = iter(["World,\n", "this is "])
    for line in sub_text:
        expected_line = next(actual_lines)
        assert line == expected_line

def test_readline_with_limit(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.readline(limit=3) == "Wor"
    assert sub_text.readline(limit=4) == "ld,\n"
    assert sub_text.readline(limit=4) == "this"
    assert sub_text.readline(limit=4) == " is "
    assert sub_text.readline(limit=4) == ""
    assert sub_text.readline(limit=4) == ""

def test_readline_with_huge_limit(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.readline(limit=100) == "World,\n"
    assert sub_text.readline(limit=100) == "this is "
    assert sub_text.readline(limit=100) == ""

def test_readline_with_zero_limit(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.readline(limit=0) == ""

def test_readlines_with_hint(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.readlines(hint=3) == ["World,\n"]
    assert sub_text.readlines(hint=3) == ["this is "]
    assert sub_text.readlines(hint=3) == []

def test_readlines_with_huge_hint(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.readlines(hint=100) == ["World,\n", "this is "]
    assert sub_text.readlines(hint=100) == []

def test_readlines_with_zero_hint(base_textio):
    sub_text = SubTextIO(base_textio, start=6, end=21)
    assert sub_text.readlines(hint=0) == ["World,\n"]
