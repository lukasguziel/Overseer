from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass

from . import imagesize

MIP_FACTOR = 4.0 / 3.0
RESIZE_PERCENTS = (25, 50, 75)
PURE_RESIZE_EXTS = frozenset({".png"})


@dataclass
class ImageInfo:
    width: int = 0
    height: int = 0
    bit_depth: int = 0
    channels: int = 0
    has_alpha: bool = False
    greyscale: bool = False
    colorspace: str = ""

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "bit_depth": self.bit_depth,
            "channels": self.channels,
            "has_alpha": self.has_alpha,
            "greyscale": self.greyscale,
            "colorspace": self.colorspace,
            "vram": vram_bytes(self.width, self.height,
                               channels=self.channels,
                               bit_depth=self.bit_depth),
        }


def vram_bytes(width: int, height: int, mipmaps: bool = True,
               channels: int = 0, bit_depth: int = 0) -> int:
    if width <= 0 or height <= 0:
        return 0
    ch = channels if 0 < channels <= 8 else 4
    bpc = bit_depth if bit_depth in (1, 2, 4, 8, 16, 32, 64) else 8
    base = int(width * height * ch * bpc / 8)
    return int(round(base * MIP_FACTOR)) if mipmaps else base


def aggregate(infos) -> dict:
    total_vram = 0
    total_pixels = 0
    count = 0
    tiers: dict = {}
    for info in infos:
        if info is None or info.width <= 0 or info.height <= 0:
            continue
        count += 1
        total_pixels += info.width * info.height
        total_vram += vram_bytes(info.width, info.height,
                                 channels=info.channels,
                                 bit_depth=info.bit_depth)
        px = max(info.width, info.height)
        tier = "8K" if px >= 8192 else "4K" if px >= 4096 \
            else "2K" if px >= 2048 else "< 2K"
        tiers[tier] = tiers.get(tier, 0) + 1
    return {"count": count, "total_pixels": total_pixels,
            "total_vram": total_vram, "tiers": tiers}


# Formats the HOST (Cinema 4D's own bitmap engine) can read and write back.
# This is the normal path inside the plugin — no third-party dependency.
# HDR/EXR stay float end to end there: no tonemapping, no depth reduction.
HOST_RESIZE_EXTS = frozenset({
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".tga", ".psd", ".exr",
    ".hdr",
})


def resize_decision(ext: str, has_pillow: bool,
                    has_host: bool = False) -> tuple[bool, str]:
    """Can this file be resized, and if not, why?

    Three engines, best first: the host's bitmap engine (always there inside
    C4D), Pillow (only if the user installed it), and the built-in PNG writer
    (dependency-free, but PNG only).
    """
    ext = (ext or "").lower()
    if has_host and ext in HOST_RESIZE_EXTS:
        return True, ""
    if has_pillow and ext in imagesize_exts():
        return True, ""
    if ext in PURE_RESIZE_EXTS:
        return True, ""
    if has_host or has_pillow:
        return False, "%s files cannot be resized" % (ext or "these")
    return False, "only PNG can be resized here"


def imagesize_exts() -> frozenset:
    return frozenset({
        ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".tga",
        ".gif", ".webp",
    })


def resize_suffix(percent: int) -> str:
    return "_%d" % int(percent)


def resize_target(path: str, percent: int) -> str:
    stem, ext = os.path.splitext(path)
    return "%s%s%s" % (stem, resize_suffix(percent), ext)


def scaled_dims(width: int, height: int, percent: int) -> tuple[int, int]:
    nw = max(1, int(round(width * percent / 100.0)))
    nh = max(1, int(round(height * percent / 100.0)))
    return nw, nh


def analyze_image(path: str) -> ImageInfo | None:
    info = _pillow_info(path)
    if info is not None:
        return info
    return _header_info(path)


def _pillow_info(path: str) -> ImageInfo | None:
    from ..vendor import import_pillow
    Image = import_pillow()
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            mode = im.mode
            w, h = im.size
            bands = len(im.getbands())
            has_alpha = "A" in im.getbands() or mode in ("RGBA", "LA", "PA")
            greyscale = mode in ("L", "LA", "I", "F", "1")
            bit_depth = _mode_bit_depth(mode)
            colorspace = ""
            if im.info.get("icc_profile"):
                colorspace = "ICC"
            elif greyscale:
                colorspace = ""
        return ImageInfo(width=int(w), height=int(h), bit_depth=bit_depth,
                         channels=bands, has_alpha=has_alpha,
                         greyscale=greyscale, colorspace=colorspace)
    except Exception:
        return None


def _mode_bit_depth(mode: str) -> int:
    if mode in ("I", "F", "I;16", "I;16B"):
        return 16 if mode.startswith("I;16") else 32
    return 8


def _header_info(path: str) -> ImageInfo | None:
    ext = os.path.splitext(path)[1].lower()
    try:
        with open(path, "rb") as f:
            head = f.read(64)
            if len(head) < 4:
                return None
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return _png_info(f, head)
            if head[:2] == b"\xff\xd8":
                return _jpeg_info(f)
            if head[:2] in (b"II", b"MM"):
                return _tiff_info(f, head)
            if head[:4] == b"\x76\x2f\x31\x01":
                return _exr_info(f)
            if head[:2] == b"BM":
                return _bmp_info(head)
            if head[:10] == b"#?RADIANCE" or head[:6] == b"#?RGBE":
                return _hdr_info(path)
    except Exception:
        return None
    if ext == ".tga":
        return _tga_info(path)
    dims = imagesize.image_size(path)
    if dims:
        return ImageInfo(width=dims[0], height=dims[1])
    return None


def _png_info(f, head) -> ImageInfo | None:
    w, h, bit_depth, color_type = struct.unpack(">IIBB", head[16:26])
    channels = {0: 1, 2: 3, 3: 3, 4: 2, 6: 4}.get(color_type, 0)
    has_alpha = color_type in (4, 6)
    greyscale = color_type in (0, 4)

    colorspace = ""
    try:
        f.seek(8)
        for _ in range(64):
            length_b = f.read(4)
            ctype = f.read(4)
            if len(length_b) < 4 or len(ctype) < 4:
                break
            length = struct.unpack(">I", length_b)[0]
            if ctype == b"sRGB":
                colorspace = "sRGB"
                break
            if ctype in (b"IDAT", b"IEND"):
                break
            f.seek(length + 4, 1)
    except Exception:
        pass
    return ImageInfo(width=int(w), height=int(h), bit_depth=int(bit_depth),
                     channels=channels, has_alpha=has_alpha,
                     greyscale=greyscale, colorspace=colorspace)


def _jpeg_info(f) -> ImageInfo | None:
    f.seek(2)
    sof = {0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7,
           0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf}
    while True:
        b = f.read(1)
        if not b:
            return None
        if b != b"\xff":
            continue
        marker = f.read(1)
        while marker == b"\xff":
            marker = f.read(1)
        if not marker:
            return None
        m = marker[0]
        if m == 0xd8 or m == 0xd9 or 0xd0 <= m <= 0xd7:
            continue
        seg = f.read(2)
        if len(seg) < 2:
            return None
        seglen = struct.unpack(">H", seg)[0]
        if m in sof:
            data = f.read(6)
            if len(data) < 6:
                return None
            prec, h, w, comps = struct.unpack(">BHHB", data)
            greyscale = comps == 1
            return ImageInfo(width=int(w), height=int(h), bit_depth=int(prec),
                             channels=int(comps), has_alpha=False,
                             greyscale=greyscale, colorspace="YCbCr")
        f.seek(seglen - 2, 1)


def _tiff_info(f, head) -> ImageInfo | None:
    endian = "<" if head[:2] == b"II" else ">"
    f.seek(4)
    off = struct.unpack(endian + "I", f.read(4))[0]
    f.seek(off)
    count_b = f.read(2)
    if len(count_b) < 2:
        return None
    count = struct.unpack(endian + "H", count_b)[0]
    tags: dict = {}
    counts: dict = {}
    offsets: dict = {}
    for _ in range(count):
        entry = f.read(12)
        if len(entry) < 12:
            break
        tag, typ, cnt = struct.unpack(endian + "HHI", entry[:8])
        counts[tag] = cnt
        if typ == 3 and cnt <= 2:
            val = struct.unpack(endian + "H", entry[8:10])[0]
        else:
            val = struct.unpack(endian + "I", entry[8:12])[0]
            if typ == 3:
                offsets[tag] = val
        tags[tag] = val
    w = tags.get(256, 0)
    h = tags.get(257, 0)
    bits = tags.get(258, 8)
    if 258 in offsets:
        try:
            f.seek(offsets[258])
            first = f.read(2)
            bits = struct.unpack(endian + "H", first)[0] if len(first) == 2 else 8
        except OSError:
            bits = 8
    samples = tags.get(277, 1)
    photometric = tags.get(262, 2)
    extra = tags.get(338, 0)
    greyscale = photometric in (0, 1)
    has_alpha = bool(extra) or samples in (2, 4)
    return ImageInfo(width=int(w), height=int(h), bit_depth=int(bits),
                     channels=int(samples), has_alpha=has_alpha,
                     greyscale=greyscale, colorspace="")


def _exr_info(f) -> ImageInfo | None:
    from .imagesize import _read_cstr  # noqa: PLC0415
    f.seek(8)
    width = height = 0
    channel_names: list = []
    pixel_bits = 16
    for _ in range(512):
        name = _read_cstr(f)
        if not name:
            break
        _read_cstr(f)
        size_b = f.read(4)
        if len(size_b) < 4:
            break
        size = struct.unpack("<I", size_b)[0]
        data = f.read(size)
        if name == "dataWindow" and len(data) >= 16:
            xmin, ymin, xmax, ymax = struct.unpack("<iiii", data[:16])
            width = xmax - xmin + 1
            height = ymax - ymin + 1
        elif name == "channels":
            channel_names, pixel_bits = _exr_channels(data)
    if not width:
        return None
    upper = [c.upper() for c in channel_names]
    has_alpha = "A" in upper
    greyscale = bool(upper) and set(upper) <= {"Y", "A"}
    ch = len(channel_names) or 3
    return ImageInfo(width=int(width), height=int(height), bit_depth=pixel_bits,
                     channels=ch, has_alpha=has_alpha, greyscale=greyscale,
                     colorspace="linear")


def _exr_channels(data: bytes) -> tuple[list, int]:
    names: list = []
    bits = 16
    i = 0
    n = len(data)
    while i < n:
        end = data.find(b"\x00", i)
        if end < 0 or end == i:
            break
        name = data[i:end].decode("latin-1", "replace")
        i = end + 1
        if i + 4 <= n:
            ptype = struct.unpack("<i", data[i:i + 4])[0]
            bits = 32 if ptype == 2 else 16
        names.append(name)
        i += 16
    return names, bits


def _bmp_info(head) -> ImageInfo | None:
    w, h = struct.unpack("<ii", head[18:26])
    bpp = struct.unpack("<H", head[28:30])[0]
    channels = 4 if bpp == 32 else 3 if bpp == 24 else 1
    return ImageInfo(width=abs(int(w)), height=abs(int(h)), bit_depth=8,
                     channels=channels, has_alpha=bpp == 32,
                     greyscale=bpp <= 8, colorspace="")


def _tga_info(path: str) -> ImageInfo | None:
    with open(path, "rb") as f:
        head = f.read(18)
    if len(head) < 18:
        return None
    img_type = head[2]
    w, h = struct.unpack("<HH", head[12:16])
    depth = head[16]
    attr_alpha = head[17] & 0x0f
    greyscale = img_type in (3, 11)
    has_alpha = depth == 32 or attr_alpha > 0
    channels = 1 if greyscale else 4 if depth == 32 else 3
    return ImageInfo(width=int(w), height=int(h), bit_depth=8,
                     channels=channels, has_alpha=has_alpha,
                     greyscale=greyscale, colorspace="")


def _hdr_info(path: str) -> ImageInfo | None:
    dims = imagesize.image_size(path)
    if not dims:
        return None
    return ImageInfo(width=dims[0], height=dims[1], bit_depth=32, channels=3,
                     has_alpha=False, greyscale=False, colorspace="linear")


def resize_file(src: str, dst: str, percent: int, has_pillow: bool) -> bool:
    if has_pillow:
        return _resize_pillow(src, dst, percent)
    if os.path.splitext(src)[1].lower() in PURE_RESIZE_EXTS:
        return _resize_png_file(src, dst, percent)
    return False


def _resize_pillow(src: str, dst: str, percent: int) -> bool:
    """Downscale with LANCZOS — the best-quality resampler Pillow offers.

    Everything that makes a texture a texture is carried over: the pixel mode
    (so RGBA keeps its alpha and an "I;16"/"F" map keeps its bit depth), the
    ICC profile, and for JPEG a high quality + 4:4:4 chroma so the copy is not
    visibly worse than the original beyond the intended downscale.
    """
    from ..vendor import import_pillow
    Image = import_pillow()
    if Image is None:
        return False
    try:
        with Image.open(src) as im:
            icc = im.info.get("icc_profile")
            nw, nh = scaled_dims(im.width, im.height, percent)
            # LANCZOS needs a float/8-bit-per-channel mode; exotic modes
            # (paletted, 1-bit) are converted, never silently mangled.
            work = im
            if im.mode in ("P", "1"):
                work = im.convert("RGBA" if "transparency" in im.info else "RGB")
            resized = work.resize((nw, nh), Image.LANCZOS)
            params = {}
            if icc:
                params["icc_profile"] = icc
            ext = os.path.splitext(dst)[1].lower()
            if ext in (".jpg", ".jpeg"):
                if resized.mode not in ("RGB", "L"):
                    resized = resized.convert("RGB")
                params.update(quality=95, subsampling=0, optimize=True)
            resized.save(dst, **params)
        return True
    except Exception:
        return False


def _resize_png_file(src: str, dst: str, percent: int) -> bool:
    try:
        with open(src, "rb") as f:
            data = f.read()
        out = resize_png_bytes(data, percent)
        if out is None:
            return False
        with open(dst, "wb") as f:
            f.write(out)
        return True
    except Exception:
        return False


def resize_png_bytes(data: bytes, percent: int):
    decoded = _png_decode(data)
    if decoded is None:
        return None
    w, h, ch, pixels = decoded
    nw, nh = scaled_dims(w, h, percent)
    out = _box_resize(pixels, w, h, ch, nw, nh)
    return _png_encode(nw, nh, ch, out)


_PNG_COLOR_CHANNELS = {0: 1, 2: 3, 4: 2, 6: 4}
_PNG_CHANNEL_COLOR = {1: 0, 2: 4, 3: 2, 4: 6}


def _png_decode(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos = 8
    width = height = bit_depth = color_type = 0
    interlace = 0
    idat = bytearray()
    n = len(data)
    while pos + 8 <= n:
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctype == b"IHDR":
            if len(body) < 13:
                return None
            width, height, bit_depth, color_type = struct.unpack(
                ">IIBB", body[:10])
            interlace = body[12]
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break
    if bit_depth != 8 or color_type not in _PNG_COLOR_CHANNELS:
        return None

    # Adam7 rows are laid out per pass, not per scanline: unfiltering them as
    # if they were sequential yields a scrambled image, so refuse instead.
    if interlace:
        return None
    ch = _PNG_COLOR_CHANNELS[color_type]
    try:
        raw = zlib.decompress(bytes(idat))
    except Exception:
        return None
    stride = width * ch
    if len(raw) < (stride + 1) * height:
        return None
    return width, height, ch, _png_unfilter(raw, width, height, ch)


def _png_unfilter(raw: bytes, width: int, height: int, ch: int) -> bytearray:
    stride = width * ch
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        pos += stride
        if ftype == 1:
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 0xff
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xff
        elif ftype == 3:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xff
        elif ftype == 4:
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                line[i] = (line[i] + _paeth(a, b, c)) & 0xff
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return out


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _box_resize(pixels, w: int, h: int, ch: int, nw: int, nh: int) -> bytearray:
    out = bytearray(nw * nh * ch)
    for oy in range(nh):
        y0 = oy * h // nh
        y1 = max(y0 + 1, (oy + 1) * h // nh)
        for ox in range(nw):
            x0 = ox * w // nw
            x1 = max(x0 + 1, (ox + 1) * w // nw)
            n = (y1 - y0) * (x1 - x0)
            base_out = (oy * nw + ox) * ch
            for c in range(ch):
                acc = 0
                for yy in range(y0, y1):
                    row = (yy * w) * ch + c
                    for xx in range(x0, x1):
                        acc += pixels[row + xx * ch]
                out[base_out + c] = (acc + n // 2) // n
    return out


def _png_encode(width: int, height: int, ch: int, pixels) -> bytes:
    color_type = _PNG_CHANNEL_COLOR.get(ch, 6)
    stride = width * ch
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += pixels[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 6)

    def chunk(ctype: bytes, body: bytes) -> bytes:
        return (struct.pack(">I", len(body)) + ctype + body
                + struct.pack(">I", zlib.crc32(ctype + body) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))
