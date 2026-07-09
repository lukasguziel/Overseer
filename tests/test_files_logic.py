import os

from sceneorg.core import files_logic as fl


def test_classify_kind_by_extension():
    # postcondition: every known extension maps to its audit kind
    assert fl.classify_kind("cache/wheel.abc") == "alembic"
    assert fl.classify_kind("refs/proxy.c4d") == "scene"
    assert fl.classify_kind("sim/smoke.vdb") == "cache"
    assert fl.classify_kind("light/soft.ies") == "ies"
    assert fl.classify_kind("audio/beep.WAV") == "audio"
    assert fl.classify_kind("plate/bg.mp4") == "video"
    assert fl.classify_kind("notes.txt") == "other"


def test_images_are_excluded_but_ies_is_not():
    # postcondition: image maps are filtered out, IES is a first-class kind
    assert fl.is_image("wood_diff.png")
    assert fl.is_image("hdri.exr")
    assert not fl.is_image("soft.ies")
    assert not fl.is_image("wheel.abc")


def test_relocatable_absolute_under_project():
    # setup: an absolute path that resolves under the project folder
    doc = os.path.join("D:", os.sep, "proj")
    resolved = os.path.join(doc, "cache", "wheel.abc")

    ok, rel = fl.relocatable(resolved, resolved, True, doc)

    # postcondition: it can become a project-relative path
    assert ok
    assert rel == "cache/wheel.abc"


def test_relocatable_rejects_outside_missing_and_relative():
    # setup
    doc = os.path.join("D:", os.sep, "proj")
    outside = os.path.join("E:", os.sep, "lib", "wheel.abc")

    # postcondition: outside the project, missing, or already-relative -> no
    assert fl.relocatable(outside, outside, True, doc) == (False, "")
    assert fl.relocatable(os.path.join(doc, "a.abc"),
                          os.path.join(doc, "a.abc"), False, doc) == (False, "")
    assert fl.relocatable("cache/wheel.abc", "cache/wheel.abc", True, doc) == (False, "")


def test_summarize_counts_by_kind_and_flags():
    # setup
    entries = [
        {"kind": "alembic", "bytes": 100, "missing": False, "absolute": True, "relocatable": True},
        {"kind": "alembic", "bytes": 50, "missing": True, "absolute": True, "relocatable": False},
        {"kind": "audio", "bytes": 10, "missing": False, "absolute": False, "relocatable": False},
    ]

    s = fl.summarize(entries)

    # postcondition
    assert s["total"] == 3
    assert s["by_kind"] == {"alembic": 2, "audio": 1}
    assert s["missing_count"] == 1
    assert s["absolute_count"] == 2
    assert s["relocatable_count"] == 1
    assert s["total_bytes"] == 160
