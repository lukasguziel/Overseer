"""Change journal persistence for the Blender backend.

Twin of cinema/adapter/journal.py. In C4D the journal travels inside the .c4d
in a BaseContainer; in Blender we store it in a scene custom property
(``scene["overseer_journal"]``, which round-trips inside the .blend) plus a
JSON sidecar next to the .blend, with a data-dir fallback. Uses the shared
``core.journal`` merge/normalise helpers unchanged.
"""
from __future__ import annotations

import json
import os

from ...core import journal as journalmod

_PROP = "overseer_journal"


def _sidecar_path(doc) -> str | None:
    try:
        path = doc.GetDocumentPath() or ""
        name = doc.GetDocumentName() or ""
    except Exception:
        return None
    if not path or not name or name == "(unsaved)":
        return None
    return os.path.join(path, name + ".sohistory.json")


def _read_json_file(path: str) -> list:
    try:
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    return []


def _write_json_file(path: str, entries: list) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _container_read(doc) -> list:
    try:
        raw = doc.scene.get(_PROP, "")
        if raw:
            return json.loads(raw) or []
    except Exception:
        pass
    return []


def _container_write(doc, entries: list) -> None:
    try:
        doc.scene[_PROP] = json.dumps(entries, ensure_ascii=False)
    except Exception:
        pass


def load_journal(doc, fallback_path: str) -> list:
    entries = journalmod.merge_journals(
        _container_read(doc), _read_json_file(_sidecar_path(doc) or ""))
    if not entries:
        entries = _read_json_file(fallback_path)
    return journalmod.normalize_journal(entries)


def save_journal(doc, entries: list, fallback_path: str) -> None:
    entries = journalmod.normalize_journal(entries)
    _container_write(doc, entries)
    side = _sidecar_path(doc)
    if side:
        _write_json_file(side, entries)
    else:
        _write_json_file(fallback_path, entries)
