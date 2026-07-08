from __future__ import annotations

import os
import struct


def resolution_tag(px: int) -> str:
    if px <= 0:
        return ""
    if px < 1024:
        return "%dpx" % px
    return "%dK" % round(px / 1024)


def image_size(path: str) -> tuple[int, int] | None:
    try:
        with open(path, "rb") as f:
            head = f.read(32)
            if len(head) < 4:
                return None

            if head[:8] == b"\x89PNG\r\n\x1a\n":
                w, h = struct.unpack(">II", head[16:24])
                return int(w), int(h)
            if head[:6] in (b"GIF87a", b"GIF89a"):
                w, h = struct.unpack("<HH", head[6:10])
                return int(w), int(h)
            if head[:2] == b"BM":
                w, h = struct.unpack("<ii", head[18:26])
                return abs(int(w)), abs(int(h))
            if head[:4] == b"8BPS":
                h, w = struct.unpack(">II", head[14:22])
                return int(w), int(h)
            if head[:4] == b"\x76\x2f\x31\x01":
                return _exr_size(f)
            if head[:12] == b"RIFF" + head[4:8] + b"WEBP" \
                    or (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
                return _webp_size(f)
            if head[:2] in (b"II", b"MM"):
                return _tiff_size(f, head)
            if head[:2] == b"\xff\xd8":
                return _jpeg_size(f)
            if head[:10] == b"#?RADIANCE" or head[:6] == b"#?RGBE":
                return _hdr_size(f)

        if os.path.splitext(path)[1].lower() == ".tga":
            return _tga_size(path)
    except Exception:
        return None
    return None


def _read_cstr(f) -> str | None:
    out = bytearray()
    while True:
        c = f.read(1)
        if not c:
            return None
        if c == b"\x00":
            return out.decode("latin-1", "replace")
        out += c


def _exr_size(f) -> tuple[int, int] | None:
    f.seek(8)
    for _ in range(512):
        name = _read_cstr(f)
        if not name:
            return None
        _read_cstr(f)
        size_b = f.read(4)
        if len(size_b) < 4:
            return None
        size = struct.unpack("<I", size_b)[0]
        data = f.read(size)
        if name == "dataWindow" and len(data) >= 16:
            xmin, ymin, xmax, ymax = struct.unpack("<iiii", data[:16])
            return xmax - xmin + 1, ymax - ymin + 1
    return None


def _webp_size(f) -> tuple[int, int] | None:
    f.seek(12)
    fmt = f.read(4)
    if fmt == b"VP8 ":
        f.seek(26)
        wh = f.read(4)
        if len(wh) < 4:
            return None
        w = struct.unpack("<H", wh[0:2])[0] & 0x3fff
        h = struct.unpack("<H", wh[2:4])[0] & 0x3fff
        return int(w), int(h)
    if fmt == b"VP8L":
        f.seek(21)
        b = f.read(4)
        if len(b) < 4:
            return None
        bits = struct.unpack("<I", b)[0]
        w = (bits & 0x3fff) + 1
        h = ((bits >> 14) & 0x3fff) + 1
        return int(w), int(h)
    if fmt == b"VP8X":
        f.seek(24)
        d = f.read(6)
        if len(d) < 6:
            return None
        w = (d[0] | (d[1] << 8) | (d[2] << 16)) + 1
        h = (d[3] | (d[4] << 8) | (d[5] << 16)) + 1
        return int(w), int(h)
    return None


def _tiff_size(f, head) -> tuple[int, int] | None:
    endian = "<" if head[:2] == b"II" else ">"
    f.seek(4)
    off = struct.unpack(endian + "I", f.read(4))[0]
    f.seek(off)
    count_b = f.read(2)
    if len(count_b) < 2:
        return None
    count = struct.unpack(endian + "H", count_b)[0]

    w = h = None
    for _ in range(count):
        entry = f.read(12)
        if len(entry) < 12:
            break
        tag, typ = struct.unpack(endian + "HH", entry[:4])
        if typ == 3:
            val = struct.unpack(endian + "H", entry[8:10])[0]
        else:
            val = struct.unpack(endian + "I", entry[8:12])[0]
        if tag == 256:
            w = val
        elif tag == 257:
            h = val

    if w and h:
        return int(w), int(h)
    return None


def _jpeg_size(f) -> tuple[int, int] | None:
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
            data = f.read(5)
            if len(data) < 5:
                return None
            h, w = struct.unpack(">HH", data[1:5])
            return int(w), int(h)
        f.seek(seglen - 2, 1)


def _hdr_size(f) -> tuple[int, int] | None:
    f.seek(0)
    for _ in range(128):
        line = f.readline()
        if not line:
            return None
        s = line.strip()
        if s[:2] in (b"-Y", b"+Y", b"-X", b"+X"):
            parts = s.split()
            if len(parts) == 4:
                try:
                    a, b = int(parts[1]), int(parts[3])
                except ValueError:
                    return None
                if parts[0][1:2] == b"Y":
                    return b, a
                return a, b
    return None


def _tga_size(path: str) -> tuple[int, int] | None:
    with open(path, "rb") as f:
        head = f.read(18)
    if len(head) < 18:
        return None
    w, h = struct.unpack("<HH", head[12:16])
    return int(w), int(h)
