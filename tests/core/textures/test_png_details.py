import struct
import zlib

from conftest import png_chunk

from overseer.core.textures import analysis as textures


def make_png_bytes(w, h, ch, interlace=0):
    color_type = {1: 0, 2: 4, 3: 2, 4: 6}[ch]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, interlace)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += bytes([(y * 8 + x) % 256 for x in range(w * ch)])
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(bytes(raw)))
            + png_chunk(b"IEND", b""))


def test_plain_png_resizes():
    # setup
    data = make_png_bytes(8, 8, 3)

    # do it
    out = textures.resize_png_bytes(data, 50)

    # postcondition
    assert out is not None
    assert textures._png_decode(out)[:3] == (4, 4, 3)


def test_interlaced_png_is_refused_not_scrambled():
    # setup: Adam7 rows are laid out per pass -- decoding them as sequential
    # scanlines would silently write a garbled texture over the material
    data = make_png_bytes(8, 8, 3, interlace=1)

    # do it
    decoded = textures._png_decode(data)
    out = textures.resize_png_bytes(data, 50)

    # postcondition
    assert decoded is None
    assert out is None


def test_interlaced_png_resize_file_reports_failure(tmp_path):
    # setup
    src = tmp_path / "wall.png"
    dst = tmp_path / "wall_50.png"
    src.write_bytes(make_png_bytes(8, 8, 4, interlace=1))

    # do it
    ok = textures.resize_file(str(src), str(dst), 50, has_pillow=False)

    # postcondition
    assert ok is False
    assert not dst.exists()


def test_truncated_ihdr_returns_none():
    # setup
    ihdr = struct.pack(">IIBB", 8, 8, 8, 6)
    data = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IEND", b""))

    # postcondition
    assert textures._png_decode(data) is None
