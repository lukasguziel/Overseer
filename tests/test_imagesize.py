"""Header-only image dimension reader (pure, no c4d)."""

import struct
import zlib

from sceneorg.core import imagesize


def test_resolution_tag():
    assert imagesize.resolution_tag(4096) == "4K"
    assert imagesize.resolution_tag(8192) == "8K"
    assert imagesize.resolution_tag(2048) == "2K"
    assert imagesize.resolution_tag(6144) == "6K"
    assert imagesize.resolution_tag(512) == "512px"
    assert imagesize.resolution_tag(0) == ""


def _write_png(path, w, h):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    chunk = struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr \
        + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    path.write_bytes(sig + chunk)


def test_png(tmp_path):
    p = tmp_path / "diffuse.png"
    _write_png(p, 4096, 4096)
    assert imagesize.image_size(str(p)) == (4096, 4096)


def test_bmp(tmp_path):
    p = tmp_path / "t.bmp"
    header = b"BM" + b"\x00" * 16 + struct.pack("<ii", 2048, 1024) + b"\x00" * 8
    p.write_bytes(header)
    assert imagesize.image_size(str(p)) == (2048, 1024)


def test_tga(tmp_path):
    p = tmp_path / "t.tga"
    head = bytearray(18)
    struct.pack_into("<HH", head, 12, 1920, 1080)
    p.write_bytes(bytes(head))
    assert imagesize.image_size(str(p)) == (1920, 1080)


def test_unknown_returns_none(tmp_path):
    p = tmp_path / "t.dat"
    p.write_bytes(b"not an image at all")
    assert imagesize.image_size(str(p)) is None


def test_missing_file_returns_none(tmp_path):
    assert imagesize.image_size(str(tmp_path / "nope.png")) is None
