import struct

from conftest import make_bmp, make_png, make_tga

from overseer.core.textures import analysis as textures
from overseer.core.textures.base import TexturePathsBase


def test_vram_estimate_includes_mipmaps():
    # setup: a 1024x1024 map is 4 MiB uncompressed RGBA
    base = 1024 * 1024 * 4

    # postcondition: the estimate adds ~1/3 for the mip chain
    assert textures.vram_bytes(1024, 1024, mipmaps=False) == base
    assert textures.vram_bytes(1024, 1024) == int(round(base * textures.MIP_FACTOR))
    assert textures.vram_bytes(0, 512) == 0


def test_vram_scales_with_channels_and_bit_depth():
    # setup: 8-bit RGBA is the default assumption
    base = textures.vram_bytes(1024, 1024, mipmaps=False)

    # postcondition: 32-bit RGBA costs 4x, 8-bit greyscale a quarter;
    # unknown metadata (0) falls back to the RGBA default
    assert textures.vram_bytes(1024, 1024, mipmaps=False,
                               channels=4, bit_depth=32) == base * 4
    assert textures.vram_bytes(1024, 1024, mipmaps=False,
                               channels=1, bit_depth=8) == base // 4
    assert textures.vram_bytes(1024, 1024, mipmaps=False,
                               channels=0, bit_depth=0) == base


def test_png_header_parser_rgba_srgb(tmp_path):
    # setup: exercise the PURE header path (Pillow, if present, has no sRGB tag)
    p = tmp_path / "diffuse.png"
    make_png(p, 64, 32, color_type=6, srgb=True)

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
    make_png(p, 64, 32, color_type=6)

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
    make_png(p, 16, 16, color_type=0)

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
    p = tmp_path / "t.tga"
    make_tga(p, 256, 128, depth=32)

    # do it
    info = textures._header_info(str(p))

    # postcondition
    assert (info.width, info.height) == (256, 128)
    assert info.channels == 4
    assert info.has_alpha is True


def test_bmp_header_parser(tmp_path):
    # setup: 32-bit BMP
    p = tmp_path / "t.bmp"
    make_bmp(p, 512, 256, bpp=32)

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


def test_tiff_multichannel_bits_resolved_via_offset(tmp_path):
    # setup: RGB TIFF whose BitsPerSample (count 3) does not fit the field —
    # the entry stores an OFFSET to the array; reading the offset as the value
    # produced absurd bit depths (and TB-scale VRAM estimates)
    def entry(tag, typ, cnt, value):
        if typ == 3 and cnt <= 2:
            return struct.pack("<HHIHH", tag, typ, cnt, value, 0)
        return struct.pack("<HHII", tag, typ, cnt, value)
    header = b"II" + struct.pack("<HI", 42, 8)
    n = 6
    bits_off = 8 + 2 + n * 12 + 4
    entries = [entry(256, 3, 1, 4096), entry(257, 3, 1, 4096),
               entry(258, 3, 3, bits_off), entry(262, 3, 1, 2),
               entry(277, 3, 1, 3), entry(339, 3, 1, 1)]
    ifd = struct.pack("<H", n) + b"".join(entries) + b"\x00" * 4
    data = header + ifd + struct.pack("<HHH", 16, 16, 16)
    p = tmp_path / "rgb16.tif"
    p.write_bytes(data)

    # do it
    info = textures._header_info(str(p))

    # postcondition: 16 bit per channel, not the raw offset
    assert info.bit_depth == 16
    assert info.channels == 3


def test_vram_clamps_bogus_metadata():
    # setup/do it/postcondition: garbage bit depth or channel counts fall back
    # to the 8-bit RGBA default instead of exploding into TB estimates
    base = textures.vram_bytes(8192, 8192, mipmaps=False)
    assert textures.vram_bytes(8192, 8192, mipmaps=False,
                               channels=3, bit_depth=36620) == base // 4 * 3
    assert textures.vram_bytes(8192, 8192, mipmaps=False,
                               channels=999, bit_depth=8) == base


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


def test_resize_decision_with_host_engine():
    # postcondition: C4D's own engine covers the render formats, incl. the
    # float ones — hdr/exr must be resizable without Pillow
    for ext in (".hdr", ".exr", ".tif", ".jpg", ".bmp", ".png"):
        ok, note = textures.resize_decision(ext, has_pillow=False, has_host=True)
        assert ok is True and note == "", ext
    assert textures.resize_decision(".xyz", has_pillow=False, has_host=True)[0] is False


def test_resize_decision_float_formats_need_the_host():
    # postcondition: Pillow alone cannot read hdr/exr — without the host
    # engine they are refused instead of tonemapped by a wrong reader
    assert textures.resize_decision(".hdr", has_pillow=True)[0] is False
    assert textures.resize_decision(".exr", has_pillow=True)[0] is False


def test_resize_target_and_dims():
    # postcondition
    assert textures.resize_target("/tex/wood.png", 50) == "/tex/wood_50.png"
    assert textures.scaled_dims(1000, 400, 25) == (250, 100)
    assert textures.scaled_dims(3, 3, 25) == (1, 1)  # never below 1px


def test_pure_png_resize_roundtrip(tmp_path):
    # setup
    src = make_png(tmp_path / "in.png", 8, 8, color_type=6)

    # do it
    out = textures.resize_png_bytes(src, 50)

    # postcondition: the resized copy is a valid, half-size PNG
    assert out is not None
    info = textures._png_decode(out)
    assert info is not None
    w, h, ch, _pixels = info
    assert (w, h, ch) == (4, 4, 4)


def test_pure_png_resize_skips_non_8bit():
    # setup
    data = make_png(None, 4, 4, bit_depth=16, pixels=False)

    # postcondition: 16-bit / indexed PNGs are declined (None), never mangled
    assert textures.resize_png_bytes(data, 50) is None


def test_texture_row_derives_display_fields_from_image_info():
    # setup
    info = textures.ImageInfo(width=2048, height=1024, bit_depth=8,
                              channels=4, has_alpha=True)

    # do it
    row = TexturePathsBase.texture_row("Wood", True, "tex\\wood.png",
                               "/p/tex/wood.png", False, True, False, "",
                               4096, info, False)
    missing = TexturePathsBase.texture_row("Wood", True, "gone.png", "", True, False,
                                   False, "", 0, None, True)

    # postcondition: metadata, vram and the basename come from the factory
    assert row["file"] == "wood.png" and row["res_tag"]
    assert row["width"] == 2048 and row["has_alpha"] is True
    assert row["vram"] == textures.vram_bytes(2048, 1024, channels=4,
                                              bit_depth=8)
    assert missing["missing"] is True and missing["vram"] == 0


def test_texture_scan_result_totals_each_physical_file_once():
    # setup
    info = textures.ImageInfo(width=512, height=512, bit_depth=8, channels=3)
    a = TexturePathsBase.texture_row("A", True, "C:/abs.png", "C:/abs.png", True,
                             True, True, "tex/abs.png", 100, info, False)
    b = TexturePathsBase.texture_row("B", True, "tex/rel.png", "/p/tex/rel.png",
                             False, False, False, "", 0, None, True)

    # do it
    out = TexturePathsBase.texture_scan_result([a, b], "/p", {"tex/rel.png"},
                                       [(100, info)])

    # postcondition
    assert out["total"] == 2 and out["absolute_count"] == 1
    assert out["relocatable_count"] == 1
    assert out["missing_count"] == 0  # the missing row is accepted
    assert out["accepted"] == ["tex/rel.png"]
    assert out["total_bytes"] == 100
    assert out["absolute"] == [a] and out["relative"] == [b]
