"""
Comprehensive tests for SubBinaryIO.

SubBinaryIO is a seekable read/write window into a contiguous byte range
[start, end) of a base BinaryIO object.  Tests are written to verify the
*specification*, not to assume the implementation is correct.
"""

from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

from multicsv.subbinaryio import SubBinaryIO


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make(data: bytes, start: int, end: int) -> tuple[io.BytesIO, SubBinaryIO]:
    """Return a (base, sub) pair.  *base* contains *data*; *sub* covers [start, end)."""
    base = io.BytesIO(data)
    return base, SubBinaryIO(base, start, end)


# ===========================================================================
# Construction
# ===========================================================================


class TestConstruction:
    def test_initial_position_is_zero(self) -> None:
        _, sub = make(b"hello", 0, 5)
        assert sub.tell() == 0

    def test_does_not_seek_base_on_construction(self) -> None:
        """Base position must not be disturbed during __init__."""
        base = io.BytesIO(b"hello world")
        base.seek(7)
        sub = SubBinaryIO(base, 0, 5)
        # SubBinaryIO was created but base position should be untouched
        assert base.tell() == 7
        # sub is usable and covers the correct region
        assert sub.read() == b"hello"

    def test_empty_region(self) -> None:
        _, sub = make(b"hello", 3, 3)
        assert sub.tell() == 0
        assert sub.read() == b""
        assert sub.readline() == b""

    def test_region_at_start(self) -> None:
        _, sub = make(b"abcdef", 0, 3)
        assert sub.read() == b"abc"

    def test_region_at_end(self) -> None:
        _, sub = make(b"abcdef", 3, 6)
        assert sub.read() == b"def"

    def test_whole_file_region(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        assert sub.read() == b"abcdef"

    def test_single_byte_region(self) -> None:
        _, sub = make(b"abcdef", 2, 3)
        assert sub.read() == b"c"


# ===========================================================================
# Protocol / capability attributes
# ===========================================================================


class TestCapabilities:
    def test_readable_delegates_to_base(self) -> None:
        """readable() must reflect base_io capability, not always True."""
        base = io.BytesIO(b"x")
        sub = SubBinaryIO(base, 0, 1)
        assert sub.readable() == base.readable()

    def test_writable_delegates_to_base(self) -> None:
        """writable() must reflect base_io capability."""
        base = io.BytesIO(b"x")
        sub = SubBinaryIO(base, 0, 1)
        assert sub.writable() == base.writable()

    def test_seekable_delegates_to_base(self) -> None:
        """seekable() must reflect base_io capability."""
        base = io.BytesIO(b"x")
        sub = SubBinaryIO(base, 0, 1)
        assert sub.seekable() == base.seekable()

    def test_readable_false_for_write_only(self, tmp_path: Path) -> None:
        """A write-only file-backed SubBinaryIO must report readable=False."""
        p = tmp_path / "wo.bin"
        p.write_bytes(b"hello")
        with open(p, "wb") as f:
            sub = SubBinaryIO(f, 0, 0)
            assert sub.readable() is False

    def test_writable_false_for_read_only(self, tmp_path: Path) -> None:
        """A read-only file-backed SubBinaryIO must report writable=False."""
        p = tmp_path / "ro.bin"
        p.write_bytes(b"hello")
        with open(p, "rb") as f:
            sub = SubBinaryIO(f, 0, 5)
            assert sub.writable() is False

    def test_name_without_base_name(self) -> None:
        """BytesIO has no name attribute; format must still return a string."""
        _, sub = make(b"x", 0, 1)
        assert isinstance(sub.name, str)
        # Must include the byte offsets
        assert "0" in sub.name
        assert "1" in sub.name

    def test_name_includes_base_name(self, tmp_path: Path) -> None:
        """For a real file, name must reflect the underlying file path."""
        p = tmp_path / "named.bin"
        p.write_bytes(b"hello")
        with open(p, "r+b") as f:
            sub = SubBinaryIO(f, 1, 4)
            assert str(p) in sub.name
            # Offsets also present
            assert "1" in sub.name
            assert "4" in sub.name

    def test_mode_inherits_from_base_bytesio(self) -> None:
        """BytesIO has no mode; mode must be derived from capabilities."""
        _, sub = make(b"x", 0, 1)
        m = sub.mode
        assert isinstance(m, str)
        assert 'b' in m

    def test_mode_inherits_from_base_file(self, tmp_path: Path) -> None:
        """Real file mode must propagate (with 'b' added if necessary)."""
        p = tmp_path / "mode.bin"
        p.write_bytes(b"hello")
        with open(p, "r+b") as f:
            sub = SubBinaryIO(f, 0, 5)
            assert 'b' in sub.mode
            assert 'r' in sub.mode

    def test_mode_read_only_file(self, tmp_path: Path) -> None:
        p = tmp_path / "ro.bin"
        p.write_bytes(b"hello")
        with open(p, "rb") as f:
            sub = SubBinaryIO(f, 0, 5)
            assert sub.mode == "rb"

    def test_mode_write_only_file(self, tmp_path: Path) -> None:
        p = tmp_path / "wo.bin"
        p.write_bytes(b"hello")
        with open(p, "wb") as f:
            sub = SubBinaryIO(f, 0, 0)
            assert sub.mode == "wb"

    def test_is_buffered_io_base(self) -> None:
        _, sub = make(b"x", 0, 1)
        assert isinstance(sub, io.BufferedIOBase)

    def test_is_io_base(self) -> None:
        _, sub = make(b"x", 0, 1)
        assert isinstance(sub, io.IOBase)

    def test_not_closed_initially(self) -> None:
        _, sub = make(b"x", 0, 1)
        assert not sub.closed


# ===========================================================================
# read()
# ===========================================================================


class TestRead:
    def test_read_all_negative_one(self) -> None:
        _, sub = make(b"abcdef", 1, 5)
        assert sub.read(-1) == b"bcde"

    def test_read_all_none(self) -> None:
        _, sub = make(b"abcdef", 1, 5)
        assert sub.read(None) == b"bcde"

    def test_read_all_no_arg(self) -> None:
        _, sub = make(b"abcdef", 1, 5)
        assert sub.read() == b"bcde"

    def test_read_zero(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        assert sub.read(0) == b""

    def test_read_partial(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        assert sub.read(3) == b"abc"

    def test_read_advances_position(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.read(2)
        assert sub.tell() == 2

    def test_read_sequential(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        assert sub.read(2) == b"ab"
        assert sub.read(2) == b"cd"
        assert sub.read(2) == b"ef"

    def test_read_at_eof_returns_empty(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.read()
        assert sub.read() == b""
        assert sub.read(5) == b""

    def test_read_does_not_exceed_region_end(self) -> None:
        """Reading more bytes than remaining must stop at the region boundary."""
        _, sub = make(b"BEFORE_content_AFTER", 7, 14)  # b"content"
        data = sub.read(9999)
        assert data == b"content"

    def test_read_clamped_to_remaining(self) -> None:
        _, sub = make(b"abcdef", 0, 4)
        sub.read(2)  # position = 2
        data = sub.read(100)  # only 2 bytes remain
        assert data == b"cd"

    def test_read_does_not_read_past_region_into_base(self) -> None:
        base = io.BytesIO(b"AAABBBCCC")
        sub = SubBinaryIO(base, 3, 6)  # b"BBB"
        assert sub.read() == b"BBB"

    def test_read_position_correct_after_partial_read(self) -> None:
        _, sub = make(b"0123456789", 2, 8)  # b"234567"
        sub.read(3)
        assert sub.tell() == 3
        assert sub.read() == b"567"
        assert sub.tell() == 6

    def test_base_position_is_modified_after_read(self) -> None:
        """SubBinaryIO seeks base_io before each operation; after a read base is left
        at abs_pos + bytes_read (not necessarily restored)."""
        base, sub = make(b"abcdef", 2, 5)
        sub.read(2)
        # base is left at 4 (2 + 2) after reading 2 bytes from position 2
        assert base.tell() == 4

    def test_read_empty_region(self) -> None:
        _, sub = make(b"abc", 2, 2)
        assert sub.read() == b""
        assert sub.read(0) == b""
        assert sub.read(5) == b""

    def test_read_returns_bytes_not_bytearray(self) -> None:
        _, sub = make(b"abc", 0, 3)
        result = sub.read()
        assert type(result) is bytes


# ===========================================================================
# read1()
# ===========================================================================


class TestRead1:
    def test_read1_returns_bytes(self) -> None:
        _, sub = make(b"abc", 0, 3)
        assert sub.read1() == b"abc"

    def test_read1_partial(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        assert sub.read1(3) == b"abc"

    def test_read1_advances_position(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.read1(2)
        assert sub.tell() == 2

    def test_read1_at_eof(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.read()
        assert sub.read1() == b""

    def test_read1_none(self) -> None:
        _, sub = make(b"abc", 0, 3)
        assert sub.read1(None) == b"abc"


# ===========================================================================
# readinto()
# ===========================================================================


class TestReadInto:
    def test_readinto_bytearray(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        buf = bytearray(6)
        n = sub.readinto(buf)
        assert n == 6
        assert buf == b"abcdef"

    def test_readinto_memoryview(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        buf = bytearray(6)
        n = sub.readinto(memoryview(buf))
        assert n == 6
        assert buf == b"abcdef"

    def test_readinto_partial_region(self) -> None:
        _, sub = make(b"XYZabcXYZ", 3, 6)  # b"abc"
        buf = bytearray(10)
        n = sub.readinto(buf)
        assert n == 3
        assert buf[:3] == b"abc"

    def test_readinto_buffer_larger_than_remaining(self) -> None:
        _, sub = make(b"ab", 0, 2)
        buf = bytearray(100)
        n = sub.readinto(buf)
        assert n == 2
        assert buf[:2] == b"ab"

    def test_readinto_empty_buffer(self) -> None:
        _, sub = make(b"abc", 0, 3)
        buf = bytearray(0)
        n = sub.readinto(buf)
        assert n == 0

    def test_readinto_at_eof(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.read()
        buf = bytearray(10)
        n = sub.readinto(buf)
        assert n == 0

    def test_readinto_advances_position(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        buf = bytearray(3)
        sub.readinto(buf)
        assert sub.tell() == 3

    def test_readinto_sequential(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        buf = bytearray(2)
        sub.readinto(buf)
        assert buf == b"ab"
        sub.readinto(buf)
        assert buf == b"cd"

    def test_readinto_does_not_modify_bytes_beyond_n(self) -> None:
        """Bytes in buf at positions >= n must be unchanged."""
        _, sub = make(b"XY", 0, 2)
        buf = bytearray(b"\xff" * 5)
        n = sub.readinto(buf)
        assert n == 2
        assert buf[2:] == b"\xff\xff\xff"


# ===========================================================================
# readline()
# ===========================================================================


class TestReadline:
    def test_readline_stops_at_newline(self) -> None:
        _, sub = make(b"line1\nline2\n", 0, 12)
        assert sub.readline() == b"line1\n"

    def test_readline_includes_newline(self) -> None:
        _, sub = make(b"abc\ndef", 0, 7)
        assert sub.readline() == b"abc\n"

    def test_readline_sequential(self) -> None:
        _, sub = make(b"a\nb\nc\n", 0, 6)
        assert sub.readline() == b"a\n"
        assert sub.readline() == b"b\n"
        assert sub.readline() == b"c\n"
        assert sub.readline() == b""

    def test_readline_no_trailing_newline(self) -> None:
        _, sub = make(b"abc", 0, 3)
        assert sub.readline() == b"abc"

    def test_readline_at_eof_returns_empty(self) -> None:
        _, sub = make(b"abc\n", 0, 4)
        sub.readline()
        assert sub.readline() == b""

    def test_readline_empty_region(self) -> None:
        _, sub = make(b"abc", 1, 1)
        assert sub.readline() == b""

    def test_readline_newline_only(self) -> None:
        _, sub = make(b"\n", 0, 1)
        assert sub.readline() == b"\n"

    def test_readline_newline_at_first_position(self) -> None:
        _, sub = make(b"\nabc", 0, 4)
        assert sub.readline() == b"\n"
        assert sub.readline() == b"abc"

    def test_readline_size_zero(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        assert sub.readline(0) == b""
        assert sub.tell() == 0

    def test_readline_size_limits_result(self) -> None:
        _, sub = make(b"abcde\nfgh", 0, 9)
        result = sub.readline(3)
        assert result == b"abc"
        assert sub.tell() == 3

    def test_readline_size_spans_newline(self) -> None:
        _, sub = make(b"abc\nde", 0, 6)
        result = sub.readline(10)
        assert result == b"abc\n"

    def test_readline_size_none(self) -> None:
        _, sub = make(b"abc\ndef", 0, 7)
        assert sub.readline(None) == b"abc\n"

    def test_readline_region_ends_before_newline_in_base(self) -> None:
        """Region [0,3] ends at base index 3; base has \n at index 5.
        readline must NOT read past the region end."""
        _, sub = make(b"abcde\nfgh", 0, 5)  # b"abcde", no \n inside
        assert sub.readline() == b"abcde"

    def test_readline_region_ends_at_newline(self) -> None:
        """Region ends exactly on a newline character."""
        _, sub = make(b"abc\ndef", 0, 4)  # b"abc\n"
        assert sub.readline() == b"abc\n"

    def test_readline_advances_position(self) -> None:
        _, sub = make(b"line1\nline2\n", 0, 12)
        sub.readline()
        assert sub.tell() == 6

    def test_readline_offset_region(self) -> None:
        """Region starting in the middle of base."""
        _, sub = make(b"XYZline1\nline2\nXYZ", 3, 15)  # b"line1\nline2\n"
        assert sub.readline() == b"line1\n"
        assert sub.readline() == b"line2\n"
        assert sub.readline() == b""


# ===========================================================================
# write()
# ===========================================================================


class TestWrite:
    def test_write_bytes(self) -> None:
        base, sub = make(b"AAAA", 0, 4)
        n = sub.write(b"BB")
        assert n == 2
        base.seek(0)
        assert base.read() == b"BBAA"

    def test_write_bytearray(self) -> None:
        base, sub = make(b"AAAA", 0, 4)
        sub.write(bytearray(b"CC"))
        base.seek(0)
        assert base.read()[:2] == b"CC"

    def test_write_memoryview(self) -> None:
        base, sub = make(b"AAAA", 0, 4)
        sub.write(memoryview(b"DD"))
        base.seek(0)
        assert base.read()[:2] == b"DD"

    def test_write_advances_position(self) -> None:
        _, sub = make(b"AAAA", 0, 4)
        sub.write(b"XY")
        assert sub.tell() == 2

    def test_write_at_offset_region(self) -> None:
        base, sub = make(b"AAABBBCCC", 3, 6)  # covers BBB
        sub.write(b"XY")
        base.seek(0)
        assert base.read() == b"AAAXYB" + b"CCC"

    def test_write_does_not_exceed_region_end(self) -> None:
        """Writing past the region end must not touch bytes outside [start, end)."""
        base, sub = make(b"AAABBBCCC", 3, 6)  # covers BBB (3 bytes)
        n = sub.write(b"XXXX")  # 4 bytes, but only 3 fit
        assert n == 3
        base.seek(0)
        assert base.read() == b"AAAXXXCCC"

    def test_write_at_end_of_region_returns_zero(self) -> None:
        _, sub = make(b"AAAA", 0, 4)
        sub.seek(0, os.SEEK_END)
        n = sub.write(b"XY")
        assert n == 0

    def test_write_visible_through_base(self) -> None:
        base, sub = make(b"HELLO", 0, 5)
        sub.write(b"WORLD")
        base.seek(0)
        assert base.read() == b"WORLD"

    def test_write_multiple_times(self) -> None:
        base, sub = make(b"AAAAAAAA", 2, 7)  # 5-byte region
        sub.write(b"12")  # writes at [2,4)
        sub.write(b"345")  # writes at [4,7)
        base.seek(0)
        assert base.read() == b"AA12345A"

    def test_write_does_not_affect_bytes_before_start(self) -> None:
        base, sub = make(b"XYZAAA", 3, 6)
        sub.write(b"BBB")
        base.seek(0)
        assert base.read()[:3] == b"XYZ"

    def test_write_does_not_affect_bytes_after_end(self) -> None:
        base, sub = make(b"AAAXYZ", 0, 3)
        sub.write(b"BBB")
        base.seek(0)
        assert base.read()[3:] == b"XYZ"

    def test_write_empty_bytes(self) -> None:
        _, sub = make(b"AAAA", 0, 4)
        n = sub.write(b"")
        assert n == 0
        assert sub.tell() == 0


# ===========================================================================
# truncate()
# ===========================================================================


class TestTruncate:
    def test_truncate_explicit_zero(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.truncate(0)
        assert sub.read() == b""

    def test_truncate_explicit_size(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.truncate(3)
        assert sub.read() == b"abc"

    def test_truncate_none_at_position(self) -> None:
        """truncate(None) truncates at current position. Position is NOT reset."""
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(2)
        sub.truncate()  # logical end is now 2; position stays at 2
        sub.seek(0)  # must seek explicitly to read from beginning
        assert sub.read() == b"ab"

    def test_truncate_clamps_position(self) -> None:
        """After truncate, position must not exceed new size."""
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(5)
        sub.truncate(3)
        assert sub.tell() <= 3

    def test_truncate_returns_new_size(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        result = sub.truncate(4)
        assert result == 4

    def test_truncate_does_not_modify_base_content(self) -> None:
        """Truncate adjusts logical end but must not write to base_io."""
        base, sub = make(b"abcdef", 0, 6)
        sub.truncate(3)
        # base still has all 6 bytes
        base.seek(0)
        assert base.read() == b"abcdef"

    def test_truncate_expand(self) -> None:
        """truncate to a size larger than current region expands _end."""
        base = io.BytesIO(b"abcdefghij")
        sub = SubBinaryIO(base, 0, 3)  # initially b"abc"
        sub.truncate(7)  # expand end to 7
        sub.seek(0)
        assert sub.read() == b"abcdefg"

    def test_truncate_at_region_start(self) -> None:
        _, sub = make(b"abcdef", 2, 5)
        sub.truncate(0)
        assert sub.read() == b""
        assert sub.tell() == 0


# ===========================================================================
# seek() and tell()
# ===========================================================================


class TestSeekTell:
    def test_seek_set_zero(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.read(3)
        sub.seek(0)
        assert sub.tell() == 0
        assert sub.read() == b"abcdef"

    def test_seek_set_middle(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(3)
        assert sub.tell() == 3
        assert sub.read() == b"def"

    def test_seek_set_to_end(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(6)
        assert sub.tell() == 6
        assert sub.read() == b""

    def test_seek_set_past_end_clamped(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        result = sub.seek(100)
        assert result == 6
        assert sub.tell() == 6

    def test_seek_set_negative_clamped_to_zero(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(3)
        result = sub.seek(-5)
        assert result == 0
        assert sub.tell() == 0

    def test_seek_cur_forward(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(2)
        sub.seek(2, os.SEEK_CUR)
        assert sub.tell() == 4

    def test_seek_cur_backward(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(4)
        sub.seek(-2, os.SEEK_CUR)
        assert sub.tell() == 2

    def test_seek_cur_past_end_clamped(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(4)
        result = sub.seek(100, os.SEEK_CUR)
        assert result == 6

    def test_seek_cur_before_start_clamped(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(2)
        result = sub.seek(-100, os.SEEK_CUR)
        assert result == 0

    def test_seek_end_zero_goes_to_end(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        result = sub.seek(0, os.SEEK_END)
        assert result == 6
        assert sub.tell() == 6

    def test_seek_end_negative_offset(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        sub.seek(-2, os.SEEK_END)
        assert sub.tell() == 4
        assert sub.read() == b"ef"

    def test_seek_end_positive_clamped(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        result = sub.seek(5, os.SEEK_END)
        assert result == 6

    def test_seek_end_before_start_clamped(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        result = sub.seek(-100, os.SEEK_END)
        assert result == 0

    def test_seek_invalid_whence_raises(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        with pytest.raises(OSError):
            sub.seek(0, 99)

    def test_seek_returns_new_position(self) -> None:
        _, sub = make(b"abcdef", 0, 6)
        assert sub.seek(3) == 3
        assert sub.seek(1, os.SEEK_CUR) == 4
        assert sub.seek(-1, os.SEEK_END) == 5

    def test_seek_set_on_offset_region(self) -> None:
        """seek() positions are relative to the start of the region, not base_io."""
        _, sub = make(b"XXXYYY", 3, 6)  # covers b"YYY"
        sub.seek(1)
        assert sub.tell() == 1
        assert sub.read() == b"YY"

    def test_tell_always_positive(self) -> None:
        _, sub = make(b"abc", 0, 3)
        for pos in [0, 1, 2, 3]:
            sub.seek(pos)
            assert sub.tell() >= 0

    def test_seek_end_empty_region(self) -> None:
        _, sub = make(b"abc", 2, 2)
        result = sub.seek(0, os.SEEK_END)
        assert result == 0


# ===========================================================================
# flush() and close()
# ===========================================================================


class TestFlushClose:
    def test_flush_does_not_close_base(self) -> None:
        base, sub = make(b"abc", 0, 3)
        sub.flush()
        assert not base.closed

    def test_flush_when_closed_does_not_raise(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.close()
        sub.flush()  # must not raise

    def test_close_marks_closed(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.close()
        assert sub.closed

    def test_close_does_not_close_base(self) -> None:
        base, sub = make(b"abc", 0, 3)
        sub.close()
        assert not base.closed

    def test_close_is_idempotent(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.close()
        sub.close()  # must not raise
        assert sub.closed

    def test_read_after_close_raises(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.close()
        with pytest.raises(ValueError):
            sub.read()

    def test_write_after_close_raises(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.close()
        with pytest.raises(ValueError):
            sub.write(b"x")

    def test_seek_after_close_raises(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.close()
        with pytest.raises(ValueError):
            sub.seek(0)

    def test_tell_after_close_raises(self) -> None:
        _, sub = make(b"abc", 0, 3)
        sub.close()
        with pytest.raises(ValueError):
            sub.tell()

    def test_readline_after_close_raises(self) -> None:
        _, sub = make(b"abc\n", 0, 4)
        sub.close()
        with pytest.raises(ValueError):
            sub.readline()

    def test_context_manager_closes(self) -> None:
        base = io.BytesIO(b"abc")
        with SubBinaryIO(base, 0, 3) as sub:
            sub.read()
        assert sub.closed
        assert not base.closed


# ===========================================================================
# Multiple views on same base_io
# ===========================================================================


class TestMultipleViews:
    def test_two_views_read_independently(self) -> None:
        base = io.BytesIO(b"AAABBBCCC")
        sub1 = SubBinaryIO(base, 0, 3)  # b"AAA"
        sub2 = SubBinaryIO(base, 3, 6)  # b"BBB"
        assert sub1.read() == b"AAA"
        assert sub2.read() == b"BBB"

    def test_two_views_interleaved_reads(self) -> None:
        base = io.BytesIO(b"abcdef")
        sub1 = SubBinaryIO(base, 0, 3)  # b"abc"
        sub2 = SubBinaryIO(base, 3, 6)  # b"def"
        assert sub1.read(1) == b"a"
        assert sub2.read(1) == b"d"
        assert sub1.read(1) == b"b"
        assert sub2.read(1) == b"e"
        assert sub1.read(1) == b"c"
        assert sub2.read(1) == b"f"

    def test_write_in_one_view_visible_in_another(self) -> None:
        base = io.BytesIO(b"AAABBB")
        sub1 = SubBinaryIO(base, 0, 3)
        sub2 = SubBinaryIO(base, 0, 3)
        sub1.write(b"XYZ")
        sub2.seek(0)
        assert sub2.read() == b"XYZ"

    def test_first_view_write_not_visible_in_non_overlapping_view(self) -> None:
        base = io.BytesIO(b"AAABBB")
        sub1 = SubBinaryIO(base, 0, 3)  # b"AAA"
        sub2 = SubBinaryIO(base, 3, 6)  # b"BBB"
        sub1.write(b"ZZZ")
        sub2.seek(0)
        assert sub2.read() == b"BBB"


# ===========================================================================
# TextIOWrapper integration
# ===========================================================================


class TestTextIOWrapper:
    def test_textiowrapper_read(self) -> None:
        base = io.BytesIO("hello\nworld\n".encode("utf-8"))
        sub = SubBinaryIO(base, 0, len(base.getvalue()))
        wrapper = io.TextIOWrapper(sub, encoding="utf-8")
        assert wrapper.read() == "hello\nworld\n"

    def test_textiowrapper_region(self) -> None:
        raw = "HEADER\ncontent line\n"
        data = raw.encode("utf-8")
        base = io.BytesIO(data)
        sub = SubBinaryIO(base, 7, len(data))  # skip "HEADER\n"
        wrapper = io.TextIOWrapper(sub, encoding="utf-8")
        assert wrapper.read() == "content line\n"

    def test_textiowrapper_readline(self) -> None:
        base = io.BytesIO(b"line1\nline2\nline3\n")
        sub = SubBinaryIO(base, 0, 18)
        wrapper = io.TextIOWrapper(sub, encoding="utf-8")
        assert wrapper.readline() == "line1\n"
        assert wrapper.readline() == "line2\n"
        assert wrapper.readline() == "line3\n"
        assert wrapper.readline() == ""

    def test_textiowrapper_seek_and_reread(self) -> None:
        base = io.BytesIO(b"hello world")
        sub = SubBinaryIO(base, 0, 11)
        wrapper = io.TextIOWrapper(sub, encoding="utf-8")
        wrapper.read()
        wrapper.seek(0)
        assert wrapper.read() == "hello world"


# ===========================================================================
# Edge cases and interactions
# ===========================================================================


class TestEdgeCases:
    def test_read_write_seek_roundtrip(self) -> None:
        base = io.BytesIO(b"AAAAAAA")
        sub = SubBinaryIO(base, 1, 6)  # 5-byte region
        sub.write(b"12345")
        sub.seek(0)
        assert sub.read() == b"12345"

    def test_read_after_write_sees_written_data(self) -> None:
        base = io.BytesIO(b"AAAAAAA")
        sub = SubBinaryIO(base, 0, 7)
        sub.write(b"XY")
        sub.seek(0)
        assert sub.read(2) == b"XY"

    def test_region_size_zero_all_ops_safe(self) -> None:
        _, sub = make(b"abc", 2, 2)
        assert sub.read() == b""
        assert sub.readline() == b""
        buf = bytearray(10)
        assert sub.readinto(buf) == 0
        assert sub.write(b"x") == 0
        assert sub.tell() == 0
        sub.seek(0)
        assert sub.tell() == 0

    def test_write_then_readline(self) -> None:
        base = io.BytesIO(b"\x00" * 11)  # 11 bytes: 6 for "hello\n" + 5 for "world"
        sub = SubBinaryIO(base, 0, 11)
        sub.write(b"hello\n")
        sub.write(b"world")
        sub.seek(0)
        assert sub.readline() == b"hello\n"
        assert sub.readline() == b"world"

    def test_truncate_then_write(self) -> None:
        _, sub = make(b"AAAAAAA", 0, 7)
        sub.truncate(3)
        sub.seek(0)
        sub.write(b"XY")
        sub.seek(0)
        assert sub.read() == b"XY" + b"A"

    def test_region_at_byte_offset_boundaries(self) -> None:
        """Verify byte offset math on a non-zero region start."""
        base = io.BytesIO(bytes(range(256)))
        sub = SubBinaryIO(base, 10, 20)
        assert sub.read() == bytes(range(10, 20))

    def test_large_region_no_copy(self) -> None:
        """SubBinaryIO must not hold a copy of the region data.
        Verify by mutating base after construction and seeing the change on read."""
        base = io.BytesIO(b"AAAA")
        sub = SubBinaryIO(base, 0, 4)
        # Mutate base after SubBinaryIO is created
        base.seek(0)
        base.write(b"ZZZZ")
        # sub must reflect the mutation (no stale copy held)
        sub.seek(0)
        assert sub.read() == b"ZZZZ"

    def test_iterate_lines(self) -> None:
        base = io.BytesIO(b"a\nb\nc\n")
        sub = SubBinaryIO(base, 0, 6)
        lines = list(sub)
        assert lines == [b"a\n", b"b\n", b"c\n"]

    def test_readlines(self) -> None:
        base = io.BytesIO(b"x\ny\nz\n")
        sub = SubBinaryIO(base, 0, 6)
        assert sub.readlines() == [b"x\n", b"y\n", b"z\n"]
