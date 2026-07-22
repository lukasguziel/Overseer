import struct
import zlib

import pytest

from overseer.core.scene import model


def png_chunk(ctype, body):
    return (struct.pack(">I", len(body)) + ctype + body
            + struct.pack(">I", zlib.crc32(ctype + body) & 0xffffffff))


def make_png(path, w, h, color_type=6, bit_depth=8, srgb=False, pixels=True):
    ihdr = struct.pack(">IIBBBBB", w, h, bit_depth, color_type, 0, 0, 0)
    data = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
    if srgb:
        data += png_chunk(b"sRGB", b"\x00")
    if pixels:
        channels = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
        raw = bytearray()
        for _y in range(h):
            raw.append(0)
            raw += bytes([128] * channels * w)
        data += png_chunk(b"IDAT", zlib.compress(bytes(raw)))
    data += png_chunk(b"IEND", b"")
    if path is not None:
        path.write_bytes(data)
    return data


def make_bmp(path, w, h, bpp=24):
    data = (b"BM" + b"\x00" * 16 + struct.pack("<ii", w, h)
            + struct.pack("<HH", 1, bpp) + b"\x00" * 16)
    path.write_bytes(data)
    return data


def make_tga(path, w, h, depth=24):
    head = bytearray(18)
    head[2] = 2
    struct.pack_into("<HH", head, 12, w, h)
    head[16] = depth
    path.write_bytes(bytes(head))
    return bytes(head)


def node(name, category=model.CAT_OTHER, type_name=None, guid=-1, children=None):
    n = model.SceneNode(
        name=name,
        type_name=type_name or category.capitalize(),
        category=category,
        guid=guid,
    )
    for c in (children or []):
        n.add_child(c)
    return n


@pytest.fixture
def sample_tree():
    """Deliberately mixed scene: partly grouped correctly, partly chaos."""
    g = [0]

    def nid(name, cat, kids=None):
        n = node(name, cat, guid=g[0], children=kids)
        g[0] += 1
        return n

    lights = nid("Lights", model.CAT_NULL, [
        nid("LIGHT_KEY", model.CAT_LIGHT),
        nid("light_fill", model.CAT_LIGHT),
    ])
    furniture = nid("Furniture", model.CAT_NULL, [
        nid("Stuhl_01", model.CAT_MESH),
        nid("Table", model.CAT_MESH),
    ])
    loose_cam = nid("KAMERA MAIN", model.CAT_CAMERA)
    exterior = nid("Exterior", model.CAT_NULL, [
        nid("Sofa", model.CAT_MESH),
        nid("Baum_02", model.CAT_MESH),
    ])
    tree = model.SceneTree(roots=[lights, furniture, loose_cam, exterior])
    return tree
