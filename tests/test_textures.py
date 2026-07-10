"""Pure texture analysis: header parsers, VRAM estimate, resize plan + PNG resize."""

import struct
import zlib

from sceneorg.core import textures


def _make_png(path, w, h, color_type=6, bit_depth=8, srgb=False):
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(ctype, body):
        return (struct.pack(">I", len(body)) + ctype + body
                + struct.pack(">I", zlib.crc32(ctype + body) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", w, h, bit_depth, color_type, 0, 0, 0)
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
    raw = bytearray()
    for _y in range(h):
        raw.append(0)
        for _x in range(w):
            raw += bytes([128] * ch)
    data = sig + chunk(b"IHDR", ihdr)
    if srgb:
        data += chunk(b"sRGB", b"\x00")
    data += chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    path.write_bytes(data)
    return data


def test_vram_estimate_includes_mipmaps():
    # setup: a 1024x1024 map is 4 MiB uncompressed RGBA
    base = 1024 * 1024 * 4

    # postcondition: the estimate adds ~1/3 for the mip chain
    assert textures.vram_bytes(1024, 1024, mipmaps=False) == base
    assert textures.vram_bytes(1024, 1024) == int(round(base * textures.MIP_FACTOR))
    assert textures.vram_bytes(0, 512) == 0


def test_png_header_parser_rgba_srgb(tmp_path):
    # setup: exercise the PURE header path (Pillow, if present, has no sRGB tag)
    p = tmp_path / "diffuse.png"
    _make_png(p, 64, 32, color_type=6, srgb=True)

    # do it
    info = textures._header_info(str(p))

    # postcondition
    assert (info.width, info.height) == (64, 32)
    assert info.channels == 4
    assert info.has_alpha is True
    assert info.greyscale is False
    assert info.bit_depth == 8
    assert info.colorspace == "sRGB"


def test_png_analysis_rgba(tmp_path):
    # setup
    p = tmp_path / "diffuse.png"
    _make_png(p, 64, 32, color_type=6)

    # do it
    info = textures.analyze_image(str(p))

    # postcondition: backend-independent fields
    assert (info.width, info.height) == (64, 32)
    assert info.channels == 4
    assert info.has_alpha is True
    assert info.greyscale is False


def test_png_analysis_greyscale(tmp_path):
    # setup
    p = tmp_path / "mask.png"
    _make_png(p, 16, 16, color_type=0)

    # do it
    info = textures._header_info(str(p))

    # postcondition
    assert info.greyscale is True
    assert info.has_alpha is False
    assert info.channels == 1


def test_jpeg_header_parser(tmp_path):
    # setup: SOI + a baseline SOF0 with 3 components, 8-bit precision
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 17, 8, 480, 640, 3) + b"\x00" * 9
    p = tmp_path / "photo.jpg"
    p.write_bytes(b"\xff\xd8" + sof + b"\xff\xd9")

    # do it
    info = textures._header_info(str(p))

    # postcondition
    assert (info.width, info.height) == (640, 480)
    assert info.channels == 3
    assert info.greyscale is False
    assert info.has_alpha is False


def test_tga_alpha_from_depth(tmp_path):
    # setup: 32-bit uncompressed truecolor TGA
    head = bytearray(18)
    head[2] = 2
    struct.pack_into("<HH", head, 12, 256, 128)
    head[16] = 32
    p = tmp_path / "t.tga"
    p.write_bytes(bytes(head))

    # do it
    info = textures._header_info(str(p))

    # postcondition
    assert (info.width, info.height) == (256, 128)
    assert info.channels == 4
    assert info.has_alpha is True


def test_bmp_header_parser(tmp_path):
    # setup: 32-bit BMP
    head = b"BM" + b"\x00" * 16 + struct.pack("<ii", 512, 256) \
        + struct.pack("<HH", 1, 32)
    p = tmp_path / "t.bmp"
    p.write_bytes(head + b"\x00" * 16)

    # do it
    info = textures._header_info(str(p))

    # postcondition
    assert (info.width, info.height) == (512, 256)
    assert info.channels == 4
    assert info.has_alpha is True


def test_tiff_header_parser(tmp_path):
    # setup: little-endian TIFF, one IFD with width/height/samples/photometric
    def ifd_entry(tag, value):
        return struct.pack("<HHII", tag, 3, 1, value)
    entries = [ifd_entry(256, 800), ifd_entry(257, 600),
               ifd_entry(258, 8), ifd_entry(262, 2), ifd_entry(277, 3)]
    ifd = struct.pack("<H", len(entries)) + b"".join(entries) + b"\x00" * 4
    data = b"II" + struct.pack("<HI", 42, 8) + ifd
    p = tmp_path / "t.tif"
    p.write_bytes(data)

    # do it
    info = textures._header_info(str(p))

    # postcondition
    assert (info.width, info.height) == (800, 600)
    assert info.channels == 3
    assert info.greyscale is False


def test_exr_header_parser(tmp_path):
    # setup: minimal EXR with a channels attr (R,G,B,A HALF) and a dataWindow
    magic = b"\x76\x2f\x31\x01" + struct.pack("<I", 2)

    def attr(name, atype, body):
        return name + b"\x00" + atype + b"\x00" + struct.pack("<I", len(body)) + body
    chans = b""
    for c in (b"A", b"B", b"G", b"R"):
        chans += c + b"\x00" + struct.pack("<iiii", 1, 0, 1, 1)
    chans += b"\x00"
    dw = struct.pack("<iiii", 0, 0, 1023, 511)
    body = magic + attr(b"channels", b"chlist", chans) \
        + attr(b"dataWindow", b"box2i", dw) + b"\x00"
    p = tmp_path / "t.exr"
    p.write_bytes(body)

    # do it
    info = textures._header_info(str(p))

    # postcondition
    assert (info.width, info.height) == (1024, 512)
    assert info.has_alpha is True
    assert info.bit_depth == 16
    assert info.colorspace == "linear"


def test_unknown_format_degrades(tmp_path):
    # setup
    p = tmp_path / "t.dat"
    p.write_bytes(b"nonsense bytes")

    # postcondition
    assert textures.analyze_image(str(p)) is None


def test_aggregate_totals(tmp_path):
    # setup
    infos = [
        textures.ImageInfo(width=8192, height=8192),
        textures.ImageInfo(width=2048, height=2048),
        None,
        textures.ImageInfo(width=0, height=0),
    ]

    # do it
    agg = textures.aggregate(infos)

    # postcondition
    assert agg["count"] == 2
    assert agg["tiers"] == {"8K": 1, "2K": 1}
    assert agg["total_vram"] == (textures.vram_bytes(8192, 8192)
                                 + textures.vram_bytes(2048, 2048))


def test_resize_decision_without_pillow():
    # postcondition: only PNG is resizable without Pillow, others get a note
    ok, note = textures.resize_decision(".png", has_pillow=False)
    assert ok is True and note == ""
    ok, note = textures.resize_decision(".jpg", has_pillow=False)
    assert ok is False and note


def test_resize_decision_with_pillow():
    # postcondition
    assert textures.resize_decision(".jpg", has_pillow=True)[0] is True
    assert textures.resize_decision(".xyz", has_pillow=True)[0] is False


def test_resize_target_and_dims():
    # postcondition
    assert textures.resize_target("/tex/wood.png", 50) == "/tex/wood_50.png"
    assert textures.scaled_dims(1000, 400, 25) == (250, 100)
    assert textures.scaled_dims(3, 3, 25) == (1, 1)  # never below 1px


def test_pure_png_resize_roundtrip(tmp_path):
    # setup
    src = _make_png(tmp_path / "in.png", 8, 8, color_type=6)

    # do it
    out = textures.resize_png_bytes(src, 50)

    # postcondition: the resized copy is a valid, half-size PNG
    assert out is not None
    info = textures._png_decode(out)
    assert info is not None
    w, h, ch, _pixels = info
    assert (w, h, ch) == (4, 4, 4)


def test_pure_png_resize_skips_non_8bit():
    # postcondition: 16-bit / indexed PNGs are declined (None), never mangled
    ihdr = struct.pack(">IIBBBBB", 4, 4, 16, 6, 0, 0, 0)

    def chunk(ctype, body):
        return (struct.pack(">I", len(body)) + ctype + body
                + struct.pack(">I", zlib.crc32(ctype + body) & 0xffffffff))
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")
    assert textures.resize_png_bytes(data, 50) is None
