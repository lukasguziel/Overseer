"""External-file audit for Blender - the NON-image external references a
``.blend`` depends on.

The Blender twin of ``cinema/audit_files.py``. Image textures are covered by
the Textures tab (``bpy.data.images``); this audit surfaces everything else the
scene points at on disk:

- linked libraries          ``bpy.data.libraries``      (kind "scene")
- Alembic / USD caches      ``bpy.data.cache_files``    (MeshSequenceCache
                            modifiers + TransformCache constraints)
- ``.mdd`` / ``.pc2`` caches  Mesh Cache modifiers       (kind "cache")
- sounds                    ``bpy.data.sounds``         (kind "audio")
- fonts                     ``bpy.data.fonts``          (kind "other")
- volumes (OpenVDB)         ``bpy.data.volumes``        (kind "cache")
- movie clips               ``bpy.data.movieclips``     (kind "video")

The ``.blend``'s own path is dropped. Blend-relative form (``//...``) is
preferred everywhere a path is rewritten. Every returned dict mirrors the C4D
audit shapes so the frozen ``FilesTab`` renders unchanged.

Ops: files_scan, files_make_relative, files_select, files_pick_path,
files_relink. NO top-level ``import bpy`` - Blender is reached only through
``adapter.bpy``.
"""
from __future__ import annotations

import os

from ..core import files_logic as fl

# Extensions Blender references that files_logic does not classify natively.
_USD_EXTS = (".usd", ".usda", ".usdc", ".usdz")
_POINT_CACHE_EXTS = (".mdd", ".pc2")


def _blend_kind(raw: str) -> str:
    """Kind label for a Blender external reference (extends ``classify_kind``
    with USD stages and the legacy point-cache formats)."""
    ext = fl.file_ext(raw)
    if ext in _USD_EXTS:
        return "scene"
    if ext in _POINT_CACHE_EXTS:
        return "cache"
    return fl.classify_kind(raw)


# ---------------------------------------------------------------------------
# path helpers (Blender ``//`` blend-relative semantics)
# ---------------------------------------------------------------------------
def _resolve(bpy, raw: str, library=None) -> str:
    """Absolute filesystem path for a (possibly ``//``-relative) reference."""
    if not raw:
        return ""
    resolved = raw
    try:
        if library is not None:
            resolved = bpy.path.abspath(raw, library=library)
        else:
            resolved = bpy.path.abspath(raw)
    except Exception:
        try:
            resolved = bpy.path.abspath(raw)
        except Exception:
            resolved = raw
    try:
        return os.path.normpath(resolved)
    except Exception:
        return resolved


def _is_blend_relative(raw: str) -> bool:
    return raw.startswith("//")


def _relocatable(raw: str, resolved: str, exists: bool, doc_path: str):
    """(relocatable, rel_target) for an absolute in-project reference.

    Unlike ``files_logic.relocatable`` this never trusts ``os.path.isabs`` for
    the relative decision - on Windows a blend-relative ``//tex/x.abc`` LOOKS
    absolute (leading ``//`` reads as UNC). A blend-relative path is already
    relative, so it is never a rewrite candidate. The target is emitted in
    Blender's ``//``-prefixed form.
    """
    if _is_blend_relative(raw):
        return False, ""
    if not (os.path.isabs(raw) and exists and doc_path):
        return False, ""
    try:
        rp = os.path.relpath(resolved, doc_path)
    except Exception:
        return False, ""
    if rp.startswith(".."):
        return False, ""
    return True, "//" + rp.replace("\\", "/")


def _prefer_relative(doc_path: str, path: str) -> str:
    """Blend-relative form of an absolute in-project path, else unchanged."""
    if doc_path and os.path.isabs(path) and not _is_blend_relative(path):
        try:
            rp = os.path.relpath(path, doc_path)
            if not rp.startswith(".."):
                return "//" + rp.replace("\\", "/")
        except Exception:
            pass
    return path


def _kept_files() -> set:
    """Paths the user accepted as missing (config ``keeps["files"]``)."""
    try:
        from ..core import keeps as keepsmod
        from . import webapi
        data = webapi._read_config_data()
        return set(keepsmod.normalize_keeps(data.get("keeps")).get("files", []))
    except Exception:
        return set()


# ---------------------------------------------------------------------------
# reference model - one holder (datablock or modifier) with a writable filepath
# ---------------------------------------------------------------------------
class _Ref:
    """A single external reference and the ``bpy`` slot that stores its path."""

    __slots__ = ("kind", "raw", "owner_name", "guid", "owner_kind",
                 "library", "_holder", "_attr")

    def __init__(self, kind, raw, owner_name, guid, library, holder,
                 attr="filepath"):
        self.kind = kind
        self.raw = raw
        self.owner_name = owner_name
        self.guid = guid
        self.owner_kind = "object" if guid is not None else ""
        self.library = library
        self._holder = holder
        self._attr = attr

    def write(self, new_path: str) -> bool:
        try:
            setattr(self._holder, self._attr, new_path)
            return True
        except Exception:
            return False


def _owner_index(adapter):
    """Reverse map data-block -> owning objects, plus inline mesh-cache
    modifier references (their path lives on the modifier, not a datablock).

    Returns ``(idx, meshcache)`` where ``idx`` maps a data-block ``id()`` to a
    list of ``(guid, obj)`` and ``meshcache`` is a list of ``(guid, obj, raw,
    modifier)``.
    """
    idx = {"sound": {}, "font": {}, "volume": {}, "cachefile": {}}
    meshcache = []
    for guid, obj in list(adapter._by_guid.items()):
        try:
            otype = obj.type
        except Exception:
            otype = ""
        try:
            data = obj.data
        except Exception:
            data = None
        if otype == "SPEAKER" and data is not None:
            snd = getattr(data, "sound", None)
            if snd is not None:
                idx["sound"].setdefault(id(snd), []).append((guid, obj))
        elif otype == "FONT" and data is not None:
            for attr in ("font", "font_bold", "font_italic",
                         "font_bold_italic"):
                f = getattr(data, attr, None)
                if f is not None:
                    idx["font"].setdefault(id(f), []).append((guid, obj))
        elif otype == "VOLUME" and data is not None:
            idx["volume"].setdefault(id(data), []).append((guid, obj))
        try:
            mods = list(obj.modifiers)
        except Exception:
            mods = []
        for m in mods:
            try:
                mtype = m.type
            except Exception:
                continue
            if mtype == "MESH_SEQUENCE_CACHE":
                cf = getattr(m, "cache_file", None)
                if cf is not None:
                    idx["cachefile"].setdefault(id(cf), []).append((guid, obj))
            elif mtype == "MESH_CACHE":
                raw = getattr(m, "filepath", "") or ""
                if raw:
                    meshcache.append((guid, obj, raw, m))
        try:
            cons = list(obj.constraints)
        except Exception:
            cons = []
        for c in cons:
            try:
                ctype = c.type
            except Exception:
                continue
            if ctype == "TRANSFORM_CACHE":
                cf = getattr(c, "cache_file", None)
                if cf is not None:
                    idx["cachefile"].setdefault(id(cf), []).append((guid, obj))
    return idx, meshcache


def _packed(db) -> bool:
    """True when the datablock's file is embedded in the .blend (no external
    dependency, so it must not be reported as a missing reference)."""
    try:
        return getattr(db, "packed_file", None) is not None
    except Exception:
        return False


def _owner_of(idx_bucket, db):
    owners = idx_bucket.get(id(db), [])
    if owners:
        guid, obj = owners[0]
        try:
            return guid, obj.name
        except Exception:
            return guid, ""
    return None, None


def _iter_refs(bpy, adapter):
    """Yield every NON-image external reference as a ``_Ref``.

    Every ``bpy.data`` access is guarded - a huge production scene has data in
    odd states and one raise must not abort the whole audit.
    """
    idx, meshcache = _owner_index(adapter)
    data = getattr(bpy, "data", None)
    if data is None:
        return

    # Linked libraries (.blend). Their filepath is relative to the current
    # file, so no per-datablock library override.
    for lib in getattr(data, "libraries", []) or []:
        try:
            raw = lib.filepath or ""
        except Exception:
            raw = ""
        if not raw:
            continue
        try:
            name = lib.name
        except Exception:
            name = os.path.basename(raw)
        yield _Ref("scene", raw, name, None, None, lib)

    # Sounds.
    for snd in getattr(data, "sounds", []) or []:
        if _packed(snd):
            continue
        try:
            raw = snd.filepath or ""
        except Exception:
            raw = ""
        if not raw:
            continue
        guid, oname = _owner_of(idx["sound"], snd)
        yield _Ref("audio", raw, oname or _safe_name(snd), guid,
                   getattr(snd, "library", None), snd)

    # Fonts (skip Blender's built-in font, filepath "<builtin>").
    for font in getattr(data, "fonts", []) or []:
        if _packed(font):
            continue
        try:
            raw = font.filepath or ""
        except Exception:
            raw = ""
        if not raw or raw == "<builtin>":
            continue
        guid, oname = _owner_of(idx["font"], font)
        yield _Ref("other", raw, oname or _safe_name(font), guid,
                   getattr(font, "library", None), font)

    # Volumes (OpenVDB sequences).
    for vol in getattr(data, "volumes", []) or []:
        if _packed(vol):
            continue
        try:
            raw = vol.filepath or ""
        except Exception:
            raw = ""
        if not raw:
            continue
        guid, oname = _owner_of(idx["volume"], vol)
        yield _Ref("cache", raw, oname or _safe_name(vol), guid,
                   getattr(vol, "library", None), vol)

    # Movie clips (footage / image sequences - distinct from bpy.data.images).
    for clip in getattr(data, "movieclips", []) or []:
        if _packed(clip):
            continue
        try:
            raw = clip.filepath or ""
        except Exception:
            raw = ""
        if not raw:
            continue
        yield _Ref("video", raw, _safe_name(clip), None,
                   getattr(clip, "library", None), clip)

    # Cache files (Alembic / USD) referenced by MeshSequenceCache modifiers or
    # TransformCache constraints.
    for cf in getattr(data, "cache_files", []) or []:
        try:
            raw = cf.filepath or ""
        except Exception:
            raw = ""
        if not raw:
            continue
        guid, oname = _owner_of(idx["cachefile"], cf)
        yield _Ref(_blend_kind(raw), raw, oname or _safe_name(cf), guid,
                   getattr(cf, "library", None), cf)

    # Mesh Cache modifiers (.mdd / .pc2) - path lives on the modifier itself.
    for guid, obj, raw, mod in meshcache:
        try:
            name = obj.name
        except Exception:
            name = ""
        yield _Ref(_blend_kind(raw), raw, name, guid, None, mod)


def _safe_name(db) -> str:
    try:
        return db.name
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------
def _entry(bpy, ref: _Ref, doc_path: str) -> dict:
    raw = ref.raw
    resolved = _resolve(bpy, raw, ref.library)
    exists = bool(resolved) and os.path.isfile(resolved)
    absolute = bool(raw) and not _is_blend_relative(raw)
    reloc, rel_target = _relocatable(raw, resolved, exists, doc_path)
    disk_bytes = 0
    if exists:
        try:
            disk_bytes = os.path.getsize(resolved)
        except Exception:
            disk_bytes = 0
    return {
        "kind": ref.kind,
        "file": os.path.basename(raw),
        "path": raw,
        "resolved": resolved,
        "exists": exists,
        "missing": not exists,
        "absolute": absolute,
        "relocatable": reloc,
        "rel_target": rel_target,
        "bytes": disk_bytes,
        "owner": ref.owner_name or "",
        "guid": ref.guid,
        "owner_kind": ref.owner_kind,
    }


def _scan(doc, adapter, progress=None) -> dict:
    bpy = adapter.bpy
    doc_path = doc.path or ""
    raw_entries = [_entry(bpy, ref, doc_path) for ref in _iter_refs(bpy, adapter)]

    # Drop the .blend's own file (a linked library could point back at it, and
    # the blend never counts as one of its own external references).
    own = os.path.normcase(os.path.normpath(doc.filepath)) if doc.filepath else ""

    def _is_own(e) -> bool:
        if not own:
            return False
        return os.path.normcase(os.path.normpath(e.get("resolved") or "")) == own

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
            "accepted": accepted, "accepted_all": sorted(kept),
            "summary": fl.summarize(entries)}


# ---------------------------------------------------------------------------
# select
# ---------------------------------------------------------------------------
def _select(doc, adapter, payload) -> dict:
    guids = [g for g in (payload.get("guids") or []) if g is not None]
    try:
        for o in doc.selected_objects():
            o.select_set(False)
    except Exception:
        pass
    selected = 0
    active_set = False
    for guid in guids:
        obj = adapter._by_guid.get(guid)
        if obj is None:
            continue
        try:
            obj.select_set(True)
            if not active_set:
                try:
                    adapter.bpy.context.view_layer.objects.active = obj
                except Exception:
                    pass
                active_set = True
            selected += 1
        except Exception:
            continue
    doc.tag_redraw()
    return {"ok": True, "selected": selected}


# ---------------------------------------------------------------------------
# make relative
# ---------------------------------------------------------------------------
def _make_relative(doc, adapter, payload) -> dict:
    doc_path = doc.path or ""
    if not doc_path:
        return {"ok": False, "fixed": 0, "skipped": 0,
                "error": "Project is not saved (no folder to make paths "
                         "relative to)."}
    bpy = adapter.bpy
    wanted = payload.get("paths")
    wanted_set = set(wanted) if wanted else None

    # Group by raw path: several holders may share one reference and are all
    # rewritten, but the path counts once (parity with C4D _rewrite_everywhere).
    targets: dict = {}
    for ref in _iter_refs(bpy, adapter):
        raw = ref.raw
        if wanted_set is not None and raw not in wanted_set:
            continue
        resolved = _resolve(bpy, raw, ref.library)
        exists = bool(resolved) and os.path.isfile(resolved)
        reloc, rel_target = _relocatable(raw, resolved, exists, doc_path)
        if not reloc or not rel_target:
            continue
        bucket = targets.setdefault(raw, [rel_target, []])
        bucket[1].append(ref)

    fixed = 0
    skipped = 0
    for _raw, (rel_target, refs) in targets.items():
        if any(r.write(rel_target) for r in refs):
            fixed += 1
        else:
            skipped += 1
    if fixed:
        doc.undo_push("Overseer: make file paths relative")
        doc.tag_redraw()
    return {"ok": True, "fixed": fixed, "skipped": skipped}


# ---------------------------------------------------------------------------
# pick path - no blocking native picker from the pump timer
# ---------------------------------------------------------------------------
def _pick_path(doc, adapter, payload) -> dict:
    return {"ok": True, "cancelled": True,
            "note": "Use Blender's file browser to relink the reference, "
                    "then rescan."}


# ---------------------------------------------------------------------------
# relink - search a folder for the missing references by basename
# ---------------------------------------------------------------------------
def _relink(doc, adapter, payload, progress) -> dict:
    folder = str(payload.get("folder") or "").strip().strip('"')
    if not folder or not os.path.isdir(folder):
        return {"error": "Folder not found: %s" % (folder or "(empty)")}
    bpy = adapter.bpy
    doc_path = doc.path or ""

    # Collect missing references (grouped by raw path -> holders).
    missing: dict = {}
    for ref in _iter_refs(bpy, adapter):
        raw = ref.raw
        resolved = _resolve(bpy, raw, ref.library)
        if resolved and os.path.isfile(resolved):
            continue
        missing.setdefault(raw, []).append(ref)
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
    for raw, refs in missing.items():
        found = index.get(os.path.basename(raw).lower())
        if found is None:
            not_found += 1
            continue
        new_path = _prefer_relative(doc_path, found)
        if any(r.write(new_path) for r in refs):
            relinked += 1
        else:
            not_found += 1
    if relinked:
        doc.undo_push("Overseer: relink missing files")
        doc.tag_redraw()
    return {"ok": True, "relinked": relinked, "not_found": not_found}


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------
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
