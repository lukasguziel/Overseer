import os

from conftest import make_png

# Load the hostapi package first so its ports module (which imports every area
# base) settles before we pull the base out directly - importing a base module
# ahead of hostapi otherwise tangles the pure-core import order.
from overseer.core.textures.base import TexturePathsBase


class FakeTexturePaths(TexturePathsBase):
    """A host-less TexturePathsBase: it only knows how to hand the template a
    list of pre-normalized refs, so the test drives the shared scan workflow."""

    def __init__(self, doc_path, refs):
        self._path = doc_path
        self._refs = refs
        self.ref_calls = 0
        self.last_include_hidden = None

    def _doc_path(self):
        return self._path

    def get_texture_refs(self, include_hidden=True):
        self.ref_calls += 1
        self.last_include_hidden = include_hidden
        yield from self._refs

    def make_textures_relative(self, materials=None):
        return {}

    def texture_owners(self, path):
        return {}

    def collect_textures(self, materials=None, subdir="tex", paths=None):
        return {}

    def relink_textures(self, folder, progress=None):
        return {}

    def clear_missing_textures(self, accepted=None):
        return {}

    def set_texture_path(self, path, new_path, material=None):
        return {}

    def texture_repath(self, paths, mode="relative", material=None):
        return {}


def test_scan_textures_builds_rows_and_counts_each_file_once(tmp_path):
    # setup: one physical file referenced by two materials
    p = tmp_path / "wood.png"
    make_png(p, 64, 32)
    resolved = str(p)
    refs = [
        ("tex/wood.png", resolved, "Wood", True, False, False, ""),
        ("tex/wood.png", resolved, "Trim", True, False, False, ""),
    ]
    host = FakeTexturePaths(str(tmp_path), refs)

    # do it
    out = host.scan_textures(include_hidden=True)

    # postcondition: the template pulled the refs from the primitive once and
    # produced the canonical scan-result shape
    assert host.ref_calls == 1 and host.last_include_hidden is True
    assert out["doc_path"] == str(tmp_path)
    assert out["total"] == 2 and out["relative_count"] == 2
    assert [r["material"] for r in out["relative"]] == ["Wood", "Trim"]
    row = out["relative"][0]
    assert row["file"] == "wood.png" and row["exists"] is True
    assert (row["width"], row["height"]) == (64, 32)
    assert row["missing"] is False
    # the physical file is analysed and its bytes counted a single time
    assert out["total_bytes"] == os.path.getsize(resolved)


def test_scan_textures_marks_missing_and_honours_accepted(tmp_path):
    # setup: an absolute reference whose file is gone, marked accepted
    missing = str(tmp_path / "gone.png")
    refs = [("gone.png", missing, "Old", False, True, False, "")]
    host = FakeTexturePaths(str(tmp_path), refs)

    # do it
    out = host.scan_textures(include_hidden=False, accepted=["gone.png"])

    # postcondition
    assert host.last_include_hidden is False
    row = out["absolute"][0]
    assert row["missing"] is True and row["bytes"] == 0 and row["vram"] == 0
    assert row["accepted"] is True
    assert out["missing_count"] == 0  # accepted rows drop out of the count
    assert out["accepted"] == ["gone.png"]
    assert out["total_bytes"] == 0
