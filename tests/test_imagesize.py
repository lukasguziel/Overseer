from conftest import make_bmp, make_png, make_tga

from sceneorg.core import imagesize


def test_resolution_tag():
    # postcondition
    assert imagesize.resolution_tag(4096) == "4K"
    assert imagesize.resolution_tag(8192) == "8K"
    assert imagesize.resolution_tag(2048) == "2K"
    assert imagesize.resolution_tag(6144) == "6K"
    assert imagesize.resolution_tag(512) == "512px"
    assert imagesize.resolution_tag(0) == ""


def test_png(tmp_path):
    # setup: header only -- a 4096x4096 pixel payload would be pointless here
    p = tmp_path / "diffuse.png"
    make_png(p, 4096, 4096, pixels=False)

    # postcondition
    assert imagesize.image_size(str(p)) == (4096, 4096)


def test_bmp(tmp_path):
    # setup
    p = tmp_path / "t.bmp"
    make_bmp(p, 2048, 1024)

    # postcondition
    assert imagesize.image_size(str(p)) == (2048, 1024)


def test_tga(tmp_path):
    # setup
    p = tmp_path / "t.tga"
    make_tga(p, 1920, 1080)

    # postcondition
    assert imagesize.image_size(str(p)) == (1920, 1080)


def test_unknown_returns_none(tmp_path):
    # setup
    p = tmp_path / "t.dat"
    p.write_bytes(b"not an image at all")

    # postcondition
    assert imagesize.image_size(str(p)) is None


def test_missing_file_returns_none(tmp_path):
    # postcondition
    assert imagesize.image_size(str(tmp_path / "nope.png")) is None
