from __future__ import annotations

from ...core.organize import journal as journalmod
from ..constants import DOC_JOURNAL_ID


def _sidecar_path(doc) -> str | None:
    import os
    try:
        path = doc.GetDocumentPath() or ""
        name = doc.GetDocumentName() or ""
    except Exception:
        return None
    if not path or not name:
        return None
    return os.path.join(path, name + ".sohistory.json")


def _read_json_file(path: str) -> list:
    import json
    import os
    try:
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    return []


def _write_json_file(path: str, entries: list) -> None:
    import json
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _container_read(doc) -> list:
    import json
    try:
        bc = doc.GetDataInstance()
        raw = bc.GetString(DOC_JOURNAL_ID) if bc is not None else ""
        if raw:
            return json.loads(raw) or []
    except Exception:
        pass
    return []


def _container_write(doc, entries: list) -> None:
    import json
    try:
        bc = doc.GetDataInstance()
        if bc is not None:
            bc.SetString(DOC_JOURNAL_ID, json.dumps(entries, ensure_ascii=False))
            doc.SetChanged()
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
