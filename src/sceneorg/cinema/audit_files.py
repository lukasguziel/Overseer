from __future__ import annotations

import os

import c4d

from ..core import files_logic as fl

_OALEMBIC = getattr(c4d, "Oalembicgenerator", 1028083)


def _alembic_path_id():
    return getattr(c4d, "ALEMBIC_PATH", None)


def _generate_path(doc_path: str, raw: str) -> str:
    try:
        return c4d.GenerateTexturePath(doc_path, raw, "") or ""
    except Exception:
        return ""


def _owner_name(owner) -> str:
    if owner is None:
        return ""
    try:
        main = owner.GetMain()
        if main is not None:
            return main.GetName()
    except Exception:
        pass
    try:
        return owner.GetName()
    except Exception:
        return ""


def _owner_kind(owner) -> str:
    if owner is None:
        return ""
    try:
        main = owner.GetMain()
    except Exception:
        main = None
    if main is None:
        main = owner
    try:
        if isinstance(main, c4d.BaseObject):
            return "object"
        if isinstance(main, c4d.BaseMaterial):
            return "material"
    except Exception:
        pass
    return ""


def _guid_for(obj, adapter) -> int | None:
    if obj is None:
        return None
    for guid, cand in adapter._by_guid.items():
        if cand is obj:
            return guid
    try:
        main = obj.GetMain()
    except Exception:
        main = None
    if main is not None and main is not obj:
        for guid, cand in adapter._by_guid.items():
            if cand is main:
                return guid
    return None


def _entry(kind: str, raw: str, owner_name: str, guid, doc_path: str,
           owner_kind: str = "") -> dict:
    resolved = _generate_path(doc_path, raw)
    exists = bool(resolved) and os.path.isfile(resolved)
    absolute = os.path.isabs(raw)
    reloc, rel_target = fl.relocatable(raw, resolved, exists, doc_path)
    disk_bytes = 0
    if exists:
        try:
            disk_bytes = os.path.getsize(resolved)
        except Exception:
            disk_bytes = 0
    return {
        "kind": kind,
        "file": os.path.basename(raw),
        "path": raw,
        "resolved": resolved,
        "exists": exists,
        "missing": not exists,
        "absolute": absolute,
        "relocatable": reloc,
        "rel_target": rel_target,
        "bytes": disk_bytes,
        "owner": owner_name,
        "guid": guid,
        # What the owner IS, so the UI does not have to guess how to select it:
        # an asset can also belong to a take or the render data, which is neither.
        "owner_kind": owner_kind,
    }


def _asset_entries(doc, adapter, doc_path: str) -> list:
    out: list = []
    filled: list = []
    try:
        flags = getattr(c4d, "ASSETDATA_FLAG_WITHCACHES",
                        getattr(c4d, "ASSETDATA_FLAG_0", 0))
        c4d.documents.GetAllAssetsNew(doc, False, "", flags, filled)
    except Exception:
        return out
    for a in filled:
        if not isinstance(a, dict):
            continue
        try:
            raw = str(a.get("filename") or "")
        except Exception:
            raw = ""
        if not raw or fl.is_image(raw):
            continue
        owner = a.get("owner")
        out.append(_entry(fl.classify_kind(raw), raw,
                          _owner_name(owner) or str(a.get("assetname") or ""),
                          _guid_for(owner, adapter), doc_path,
                          _owner_kind(owner)))
    return out


def _alembic_entries(adapter, doc_path: str) -> list:
    out: list = []
    pid = _alembic_path_id()
    if pid is None:
        return out
    for guid, op in adapter._by_guid.items():
        try:
            if op.GetType() != _OALEMBIC:
                continue
            raw = str(op[pid] or "")
        except Exception:
            continue
        if not raw:
            continue
        out.append(_entry("alembic", raw, op.GetName(), guid, doc_path, "object"))
    return out


def _kept_files() -> set:
    try:
        from ..core import keeps as keepsmod
        from . import webapi
        data = webapi._read_config_data()
        return set(keepsmod.normalize_keeps(data.get("keeps")).get("files", []))
    except Exception:
        return set()


def _scan(doc, adapter, progress=None) -> dict:
    import os
    doc_path = doc.GetDocumentPath() or ""
    raw_entries = _asset_entries(doc, adapter, doc_path) + \
        _alembic_entries(adapter, doc_path)

    doc_name = doc.GetDocumentName() or ""
    own = os.path.normcase(os.path.join(doc_path, doc_name))
    own_name = os.path.normcase(doc_name)

    def _is_own(e) -> bool:
        if os.path.normcase(e.get("resolved") or "") == own:
            return True
        # An unsaved document has no path, so its own entry never resolves and
        # would show up as a missing file — match it by name instead.
        return (not doc_path) and bool(own_name) \
            and os.path.normcase(e.get("file") or "") == own_name

    raw_entries = [e for e in raw_entries if not _is_own(e)]

    entries: list = []
    seen: set = set()
    for e in raw_entries:
        key = (e["kind"], e["path"], e["owner"])
        if key in seen:
            continue
        seen.add(key)
        entries.append(e)

    kept = _kept_files()
    accepted = sorted({e["path"] for e in entries
                       if e["missing"] and e["path"] in kept})
    entries = [e for e in entries
               if not (e["missing"] and e["path"] in kept)]

    entries.sort(key=lambda e: e["bytes"], reverse=True)
    return {"ok": True, "doc_path": doc_path, "entries": entries,
            "accepted": accepted, "summary": fl.summarize(entries)}


def _holders(adapter):
    seen: set = set()
    for obj in adapter._by_guid.values():
        if id(obj) not in seen:
            seen.add(id(obj))
            yield obj
    for holder in adapter._all_material_holders():
        if id(holder) not in seen:
            seen.add(id(holder))
            yield holder


def _rewrite_everywhere(doc, adapter, raw: str, new_path: str) -> int:
    written = 0
    done: set = set()
    for holder in _holders(adapter):
        for h, pid in adapter._find_path_params(holder, raw):
            key = (id(h), str(pid))
            if key in done:
                continue
            done.add(key)
            try:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, h)
                h[pid] = new_path
                written += 1
            except Exception:
                continue
    return written


def _prefer_relative(doc, path: str) -> str:
    doc_path = doc.GetDocumentPath() or ""
    if doc_path and os.path.isabs(path):
        try:
            rp = os.path.relpath(path, doc_path)
            if not rp.startswith(".."):
                return rp.replace("\\", "/")
        except Exception:
            pass
    return path


def _pick_path(doc, adapter, payload) -> dict:
    raw = str(payload.get("path") or "")
    try:
        chosen = c4d.storage.LoadDialog(
            type=c4d.FILESELECTTYPE_ANYTHING,
            title="Pick replacement for %s" % os.path.basename(raw),
            flags=c4d.FILESELECT_LOAD,
            def_path=doc.GetDocumentPath() or "")
    except Exception as ex:  # noqa: BLE001
        return {"error": "file dialog failed: %s" % ex}
    if not chosen:
        return {"ok": True, "cancelled": True}
    doc.StartUndo()
    changed = _rewrite_everywhere(doc, adapter, raw,
                                  _prefer_relative(doc, chosen))
    doc.EndUndo()
    c4d.EventAdd()
    if not changed:
        return {"error": "reference not found in the scene"}
    return {"ok": True, "picked": chosen, "changed": changed}


def _relink(doc, adapter, payload, progress) -> dict:
    folder = str(payload.get("folder") or "").strip().strip('"')
    if not folder or not os.path.isdir(folder):
        return {"error": "Folder not found: %s" % (folder or "(empty)")}
    scan = _scan(doc, adapter)
    missing = [e for e in scan["entries"] if e["missing"]]
    if not missing:
        return {"ok": True, "relinked": 0, "not_found": 0}

    index: dict = {}
    count = 0
    for root, _dirs, files in os.walk(folder):
        for fn in files:
            count += 1
            if progress and count % 200 == 0:
                progress("Indexing search folder", 0, 0, root)
            index.setdefault(fn.lower(), os.path.join(root, fn))

    relinked = not_found = 0
    doc.StartUndo()
    for e in missing:
        found = index.get(os.path.basename(e["path"]).lower())
        if found is None:
            not_found += 1
            continue
        if _rewrite_everywhere(doc, adapter, e["path"],
                               _prefer_relative(doc, found)):
            relinked += 1
        else:
            not_found += 1
    doc.EndUndo()
    c4d.EventAdd()
    return {"ok": True, "relinked": relinked, "not_found": not_found}


def _make_relative(doc, adapter, payload) -> dict:
    doc_path = doc.GetDocumentPath() or ""
    if not doc_path:
        return {"ok": False, "fixed": 0, "skipped": 0,
                "error": "Project is not saved (no folder to make paths relative to)."}
    wanted = payload.get("paths")
    wanted_set = set(wanted) if wanted else None
    pid = _alembic_path_id()

    scan = _scan(doc, adapter)
    targets: list = []
    skipped = 0
    for e in scan["entries"]:
        if not e["relocatable"]:
            continue
        if wanted_set is not None and e["path"] not in wanted_set:
            continue
        obj = adapter._by_guid.get(e["guid"]) if e["guid"] is not None else None
        if e["kind"] == "alembic" and obj is not None and pid is not None:
            targets.append((obj, e["rel_target"]))
        else:
            skipped += 1

    if not targets:
        return {"ok": True, "fixed": 0, "skipped": skipped}

    doc.StartUndo()
    fixed = 0
    for obj, rel in targets:
        try:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj[pid] = rel
            fixed += 1
        except Exception:
            skipped += 1
    doc.EndUndo()
    c4d.EventAdd()
    return {"ok": True, "fixed": fixed, "skipped": skipped}


def _select(doc, adapter, payload) -> dict:
    guids = [g for g in (payload.get("guids") or []) if g is not None]
    selected = 0
    first = True
    for guid in guids:
        obj = adapter._by_guid.get(guid)
        if obj is None:
            continue
        try:
            if first:
                doc.SetActiveObject(obj, c4d.SELECTION_NEW)
                first = False
            else:
                obj.SetBit(c4d.BIT_ACTIVE)
            selected += 1
        except Exception:
            continue
    try:
        c4d.EventAdd()
    except Exception:
        pass
    return {"ok": True, "selected": selected}


def handle(op, payload, doc, adapter, tree, progress) -> dict:
    if op == "files_scan":
        return _scan(doc, adapter, progress)
    if op == "files_make_relative":
        return _make_relative(doc, adapter, payload)
    if op == "files_select":
        return _select(doc, adapter, payload)
    if op == "files_pick_path":
        return _pick_path(doc, adapter, payload)
    if op == "files_relink":
        return _relink(doc, adapter, payload, progress)
    return {"error": "unknown files op: %s" % op}
