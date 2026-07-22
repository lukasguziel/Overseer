import base64
from io import BytesIO

import pytest

from overseer.core.textures import thumbs as texthumbs


def test_supported_by_extension():
    assert texthumbs.supported("maps/wood_diffuse.JPG")
    assert texthumbs.supported("wood.tiff")
    assert not texthumbs.supported("sky.exr")
    assert not texthumbs.supported("light.hdr")
    assert not texthumbs.supported("")


def test_thumbnail_missing_or_unsupported(tmp_path):
    assert texthumbs.thumbnail(str(tmp_path / "gone.png")) is None
    exr = tmp_path / "sky.exr"
    exr.write_bytes(b"\x76\x2f\x31\x01")
    assert texthumbs.thumbnail(str(exr)) is None


def test_thumbnail_data_uri(tmp_path):
    image_mod = pytest.importorskip("PIL.Image")
    src = tmp_path / "map.png"
    image_mod.new("RGB", (16, 9), (200, 40, 40)).save(src)
    uri = texthumbs.thumbnail(str(src), size=8)
    assert uri is not None and uri.startswith("data:image/png;base64,")
    img = image_mod.open(BytesIO(base64.b64decode(uri.split(",", 1)[1])))
    # Squashed to a square, matching the host bitmap engines' look.
    assert img.size == (8, 8)
