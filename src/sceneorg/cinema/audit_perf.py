"""[c4d] Rebuild-cost audit: which generator stalls the viewport.

How it measures: a generator only rebuilds its cache when it is dirty, so we
mark exactly ONE object's cache dirty and time a full scene pass. What the
clock sees is that object's rebuild (plus the generators above it in the
chain, which C4D has to rebuild too — that is real cost, not an artifact:
a heavy Cloner under a Subdivision Surface genuinely drags the whole branch).
Nothing in the document changes — DIRTYFLAGS_CACHE only invalidates the
cache, it does not touch the object's data, so no undo step and no dirty doc.
"""
from __future__ import annotations

import time

import c4d

from ..core import perf_logic

_BUILDFLAGS = getattr(c4d, "BUILDFLAGS_0", getattr(c4d, "BUILDFLAGS_NONE", 0))
_DIRTY_CACHE = getattr(c4d, "DIRTYFLAGS_CACHE", getattr(c4d, "DIRTYFLAGS_DATA", 0))

# How often each object is measured; the FASTEST run counts (the slow ones
# carry whatever else the machine was doing — the minimum is the honest cost).
_REPEATS = 2


def _exec_passes(doc) -> float:
    """Run one scene pass and return how long it took, in seconds."""
    t0 = time.perf_counter()
    try:
        doc.ExecutePasses(None, False, True, True, _BUILDFLAGS)
    except Exception:
        pass
    return time.perf_counter() - t0


def _is_candidate(obj) -> bool:
    try:
        info = obj.GetInfo()
    except Exception:
        return False
    gen = getattr(c4d, "OBJECT_GENERATOR", 0)
    mod = getattr(c4d, "OBJECT_MODIFIER", 0)
    return bool(info & (gen | mod))


def _type_label(obj) -> str:
    from .constants import KNOWN_TYPES
    try:
        tid = obj.GetType()
    except Exception:
        return "Object"
    return KNOWN_TYPES.get(tid, "Type %d" % tid)


def _candidates(adapter, tree) -> list:
    out = []
    for node in tree.walk():
        obj = adapter._by_guid.get(node.guid)
        if obj is None or not _is_candidate(obj):
            continue
        out.append((node, obj))
    return out


def has_any(adapter, tree) -> bool:
    for node in tree.walk():
        obj = adapter._by_guid.get(node.guid)
        if obj is not None and _is_candidate(obj):
            return True
    return False


def _scan(payload, doc, adapter, tree, progress):
    cands = _candidates(adapter, tree)
    if not cands:
        return {"ok": True, "entries": [],
                "summary": {"total": 0, "measured": 0, "total_ms": 0.0,
                            "heavy": 0, "slowest": "", "slowest_ms": 0.0,
                            "slowest_share": 0.0},
                "baseline_ms": 0.0}

    repeats = max(1, min(5, int(payload.get("repeats") or _REPEATS)))

    # Warm up (everything gets built once), then time a pass with nothing
    # dirty — that is the fixed overhead of a pass, which we subtract below.
    _exec_passes(doc)
    baseline = min(_exec_passes(doc) for _ in range(2))

    entries = []
    total = len(cands)
    for i, (node, obj) in enumerate(cands):
        progress("Measuring rebuild times", i, total, node.name)
        best = None
        for _ in range(repeats):
            try:
                obj.SetDirty(_DIRTY_CACHE)
            except Exception:
                break
            dt = _exec_passes(doc)
            best = dt if best is None else min(best, dt)
        if best is None:
            continue
        entries.append({
            "guid": node.guid,
            "name": node.name,
            "type": _type_label(obj),
            "ms": max(0.0, (best - baseline) * 1000.0),
            "polygons": getattr(node, "polygons", 0) or 0,
        })

    # Calibration: rebuild EVERYTHING at once. If the per-object times were
    # perfectly isolated, they would add up to this. They add up to more when
    # a generator sits under another one (rebuilding the child forces the
    # parent too, so the parent's cost is counted in several children) — the
    # ratio tells the user how much to trust a single row.
    progress("Measuring rebuild times", total, total, "full scene")
    scene_ms = 0.0
    for _ in range(repeats):
        for _node, obj in cands:
            try:
                obj.SetDirty(_DIRTY_CACHE)
            except Exception:
                pass
        dt = _exec_passes(doc)
        scene_ms = dt if scene_ms == 0.0 else min(scene_ms, dt)
    scene_ms = max(0.0, (scene_ms - baseline) * 1000.0)

    result = perf_logic.rank(entries)
    result["ok"] = True
    result["baseline_ms"] = baseline * 1000.0
    result["scene_ms"] = scene_ms
    result["summary"]["scene_ms"] = scene_ms
    result["summary"]["overlap"] = perf_logic.overlap_ratio(
        result["summary"]["total_ms"], scene_ms)
    return result


def _select(payload, doc, adapter, tree, progress):
    guids = payload.get("guids") or []
    selected = 0
    for guid in guids:
        obj = adapter._by_guid.get(int(guid))
        if obj is None:
            continue
        mode = c4d.SELECTION_NEW if selected == 0 else c4d.SELECTION_ADD
        try:
            doc.SetActiveObject(obj, mode)
            obj.SetBit(c4d.BIT_ACTIVE)
            selected += 1
        except Exception:
            pass
    c4d.EventAdd()
    return {"ok": True, "selected": selected}


def handle(op, payload, doc, adapter, tree, progress):
    if op == "perf_scan":
        return _scan(payload, doc, adapter, tree, progress)
    if op == "perf_select":
        return _select(payload, doc, adapter, tree, progress)
    return {"error": "unknown op: %s" % op}
