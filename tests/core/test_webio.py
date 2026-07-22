"""Unit tests for the host-neutral webio helpers (no ``bpy`` / ``c4d``).

``core/webio.py`` is the shared IO layer both backends route through; these
cover the pure helpers with tmp dirs only.
"""
from __future__ import annotations

import csv
import os

from overseer.core import webio


# ---------------------------------------------------------------------------
# config.json read/write
# ---------------------------------------------------------------------------
def test_config_round_trip(tmp_path):
    path = str(tmp_path / "config.json")
    data = {"casing": "PascalCase", "port": 8787, "keeps": {"naming": ["Keep"]}}

    webio.write_config_data(path, data)

    assert webio.read_config_data(path) == data


def test_read_missing_config_is_empty(tmp_path):
    assert webio.read_config_data(str(tmp_path / "nope.json")) == {}


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------
def test_write_csv_writes_header_and_rows(tmp_path):
    report = {"nodes": [
        {"path": "/A", "name": "A", "type": "Mesh", "category": "mesh",
         "depth": 0, "casing": "PascalCase", "language": "en", "children": 1,
         "polygons": 12},  # extra key is ignored by extrasaction="ignore"
        {"path": "/A/B", "name": "B", "type": "Empty", "category": "null",
         "depth": 1, "casing": "PascalCase", "language": "en", "children": 0},
    ]}
    out = str(tmp_path / "structure.csv")

    result = webio.write_csv(report, out)

    assert result is not None
    path, rows = result
    assert rows == 2
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        assert reader.fieldnames == list(webio.CSV_FIELDS)
        parsed = list(reader)
    assert [r["name"] for r in parsed] == ["A", "B"]
    assert "polygons" not in parsed[0]      # not part of CSV_FIELDS


def test_write_csv_target_dir_takes_precedence(tmp_path):
    target = tmp_path / "next-to-blend"
    target.mkdir()
    report = {"nodes": [{"path": "/A", "name": "A"}]}

    result = webio.write_csv(report, str(tmp_path / "fallback.csv"),
                             target_dir=str(target))

    assert result is not None
    assert result[0] == str(target / "scene_structure.csv")


# ---------------------------------------------------------------------------
# analysis history round-trip
# ---------------------------------------------------------------------------
def _entry(file_name, ts, objects=0):
    return {"file": file_name, "ts": ts, "at": "now", "objects": objects,
            "polys": 0, "size": 0}


def test_history_round_trip_and_append(tmp_path):
    path = str(tmp_path / "hist.json")

    webio.record_history(path, _entry("scene.blend", 1000.0, objects=3))
    first = webio.read_history(path)
    assert len(first) == 1
    assert first[0]["objects"] == 3

    # A different file appends a second entry.
    webio.record_history(path, _entry("other.blend", 2000.0, objects=7))
    two = webio.read_history(path)
    assert [e["file"] for e in two] == ["scene.blend", "other.blend"]


def test_history_coalesces_same_file_within_a_minute(tmp_path):
    path = str(tmp_path / "hist.json")

    webio.record_history(path, _entry("scene.blend", 1000.0, objects=3))
    # Same file, <60s apart -> replaces the last entry rather than appending.
    webio.record_history(path, _entry("scene.blend", 1030.0, objects=9))

    hist = webio.read_history(path)
    assert len(hist) == 1
    assert hist[0]["objects"] == 9


def test_history_path_uses_slug(tmp_path):
    p = webio.history_path(str(tmp_path / "history"), "scene-blend-abc")
    assert p.endswith("scene-blend-abc.json")
    assert os.path.isdir(os.path.dirname(p))


# ---------------------------------------------------------------------------
# data-dir resolution
# ---------------------------------------------------------------------------
def test_resolve_data_dir_prefers_writable_plugin_dir(tmp_path):
    plugin = tmp_path / "plugin"
    plugin.mkdir()

    got = webio.resolve_data_dir(str(plugin), None)

    assert got == str(plugin)


def test_resolve_data_dir_falls_back_to_prefs_base(tmp_path):
    # A plugin dir that does not exist is not writable -> use prefs_base.
    plugin = str(tmp_path / "does-not-exist")
    prefs = tmp_path / "prefs"
    prefs.mkdir()

    got = webio.resolve_data_dir(plugin, str(prefs), app_name="overseer")

    assert got == str(prefs / "overseer")
    assert os.path.isdir(got)


def test_resolve_data_dir_migrates_legacy_folder(tmp_path):
    plugin = str(tmp_path / "missing")
    prefs = tmp_path / "prefs"
    legacy = prefs / "scene_organizer"
    legacy.mkdir(parents=True)
    (legacy / "config.json").write_text("{}", encoding="utf-8")

    got = webio.resolve_data_dir(plugin, str(prefs), app_name="overseer",
                                 legacy_name="scene_organizer")

    # Legacy folder was renamed to the new app name, keeping its contents.
    assert got == str(prefs / "overseer")
    assert os.path.isfile(os.path.join(got, "config.json"))
