"""The Blender webapi answers the SAME JSON shapes as the C4D backend.

The frontend is frozen and shared verbatim, so every ``/api`` op must return the
C4D contract key-for-key. These tests drive ``overseer.blender.webapi.handle``
over a fake ``bpy`` and assert the top-level shape of the three ops the
foundation already fully implements (``dirty``, ``netinfo``, ``analyze``). The
domain mixins are still stubs, so we assert only on keys the foundation
produces - not on material/texture/layer contents.
"""
from __future__ import annotations

import os

import fakebpy
import pytest

from overseer.blender import webapi


@pytest.fixture
def blender_scene():
    """Build a synthetic scene, install it as ``sys.modules['bpy']`` and tear
    it down afterwards so the fake never leaks into the bpy-free suite."""
    def _factory(*args, **kwargs) -> fakebpy.FakeBpy:
        fake = fakebpy.make_scene(*args, **kwargs)
        fakebpy.install(fake)
        return fake

    yield _factory
    fakebpy.reset()

SCENE = [
    {"name": "Rig", "type": "EMPTY"},
    {"name": "Body", "type": "MESH", "parent": "Rig",
     "pts": 8, "polys": 6, "collection": "Props"},
    {"name": "Cam", "type": "CAMERA", "selected": True},
    {"name": "Sun", "type": "LIGHT"},
]


@pytest.fixture
def sandbox_paths(tmp_path, monkeypatch):
    """Redirect every file the webapi writes into a tmp dir - by default the
    data dir resolves to the (writable) source tree. The op logic now lives in
    the shared ``WebApi`` instance (``webapi._api``), so the path attributes are
    patched there."""
    data = tmp_path / "data"
    history = data / "history"
    data.mkdir()
    history.mkdir()
    api = webapi._api
    for attr, path in {
        "DATA_DIR": data,
        "CONFIG_PATH": data / "config.json",
        "EXPORT_PATH": data / "scene_report.json",
        "EXPORT_CSV_PATH": data / "scene_structure.csv",
        "HISTORY_DIR": history,
        "HISTORY_PATH": data / "analysis_history.json",
        "CHANGES_PATH": data / "change_history.json",
        "GOOGLE_CACHE_PATH": data / "google_cache.json",
    }.items():
        monkeypatch.setattr(api, attr, str(path))
    return data


def test_dirty_contract(blender_scene, sandbox_paths):
    blender_scene(SCENE, collections=["Props"])

    res = webapi.handle({"op": "dirty"})

    assert set(res) == {"ok", "dirty", "name", "sel", "sel_names", "sel_count"}
    assert res["ok"] is True
    assert isinstance(res["dirty"], int)
    assert res["name"] == "demo.blend"
    assert res["sel_count"] == 1              # only Cam is selected
    assert res["sel_names"] == ["Cam"]


def test_netinfo_contract(blender_scene, sandbox_paths):
    blender_scene(SCENE)

    res = webapi.handle({"op": "netinfo"})

    assert set(res) == {"ok", "lan", "wanted", "restart_needed", "ip", "port"}
    assert res["ok"] is True
    assert isinstance(res["lan"], bool)
    assert isinstance(res["wanted"], bool)
    assert isinstance(res["restart_needed"], bool)
    assert isinstance(res["port"], int)


def test_analyze_contract(blender_scene, sandbox_paths):
    blender_scene(SCENE, collections=["Props"])

    res = webapi.handle({"op": "analyze", "settings": {}})

    # Envelope: same three top-level keys the C4D _op_analyze returns.
    assert res["ok"] is True
    assert "report" in res
    assert "export_path" in res

    report = res["report"]
    # Core analyzer fields (parity with SceneReport.to_dict()).
    for key in ("object_count", "max_depth", "total_points", "total_polys",
                "types", "categories", "casing", "language", "nodes",
                "top_level", "layers_by_name", "no_layer_count"):
        assert key in report, "missing report key: %s" % key

    # Blender-side augmentation the frontend also expects.
    for key in ("scoped", "include_hidden", "dirty", "doc_name", "sel",
                "file_size", "materials", "textures", "layers_report",
                "has_generators", "has_sims", "analyzed_at"):
        assert key in report, "missing augmented key: %s" % key

    assert report["object_count"] == len(SCENE)
    assert report["categories"] == {"null": 1, "mesh": 1, "camera": 1,
                                    "light": 1}
    assert report["doc_name"] == "demo.blend"
    # A report was written to the sandbox, not the source tree.
    assert res["export_path"] is not None
    assert os.path.dirname(res["export_path"]) == str(sandbox_paths)


def test_unknown_op_is_reported(blender_scene, sandbox_paths):
    blender_scene(SCENE)

    res = webapi.handle({"op": "does_not_exist"})

    assert "error" in res
    assert "does_not_exist" in res["error"]
