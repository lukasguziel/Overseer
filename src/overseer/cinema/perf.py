from __future__ import annotations

import time

import c4d

from ..core.perf import logic as perf_logic
from ..core.perf.audit import PerfAudit

_BUILDFLAGS = getattr(c4d, "BUILDFLAGS_0", getattr(c4d, "BUILDFLAGS_NONE", 0))
_DIRTY_CACHE = getattr(c4d, "DIRTYFLAGS_CACHE", getattr(c4d, "DIRTYFLAGS_DATA", 0))

_REPEATS = 3


class CinemaPerfAudit(PerfAudit):
    """Viewport rebuild-cost audit (Cinema 4D host)."""

    def _exec_passes(self, doc) -> float:
        t0 = time.perf_counter()
        try:
            doc.ExecutePasses(None, False, True, True, _BUILDFLAGS)
        except Exception:
            pass
        return time.perf_counter() - t0

    def _is_candidate(self, obj) -> bool:
        try:
            info = obj.GetInfo()
        except Exception:
            return False
        gen = getattr(c4d, "OBJECT_GENERATOR", 0)
        mod = getattr(c4d, "OBJECT_MODIFIER", 0)
        return bool(info & (gen | mod))

    def _type_label(self, obj) -> str:
        from .constants import KNOWN_TYPES
        try:
            name = obj.GetTypeName()
            if name:
                return str(name)
        except Exception:
            pass
        try:
            tid = obj.GetType()
        except Exception:
            return "Object"
        return KNOWN_TYPES.get(tid, "Object")

    def _candidates(self, adapter, tree) -> list:
        out = []
        for node in tree.walk():
            obj = adapter._by_guid.get(node.guid)
            if obj is None or not self._is_candidate(obj):
                continue
            out.append((node, obj))
        return out

    def has_any(self, adapter, tree) -> bool:
        for node in tree.walk():
            obj = adapter._by_guid.get(node.guid)
            if obj is not None and self._is_candidate(obj):
                return True
        return False

    def scan(self, doc, adapter, tree, payload, progress) -> dict:
        cands = self._candidates(adapter, tree)
        if not cands:
            return {"ok": True, "entries": [],
                    "summary": {"total": 0, "measured": 0, "total_ms": 0.0,
                                "heavy": 0, "slowest": "", "slowest_ms": 0.0,
                                "slowest_share": 0.0, "scene_ms": 0.0,
                                "overlap": 0.0},
                    "baseline_ms": 0.0, "scene_ms": 0.0}

        repeats = max(1, min(5, int(payload.get("repeats") or _REPEATS)))

        self._exec_passes(doc)
        baseline = perf_logic.median([self._exec_passes(doc) for _ in range(repeats)])

        entries = []
        total = len(cands)
        for i, (node, obj) in enumerate(cands):
            progress("Measuring rebuild times", i, total, node.name)
            samples = []
            for _ in range(repeats):
                try:
                    obj.SetDirty(_DIRTY_CACHE)
                except Exception:
                    break
                samples.append(self._exec_passes(doc))
            if not samples:
                continue
            entries.append(perf_logic.measure_row(
                node.guid, node.name, self._type_label(obj), samples,
                baseline, getattr(node, "polygons", 0) or 0))

        progress("Measuring rebuild times", total, total, "full scene")
        scene_runs = []
        for _ in range(repeats):
            for _node, obj in cands:
                try:
                    obj.SetDirty(_DIRTY_CACHE)
                except Exception:
                    pass
            scene_runs.append(self._exec_passes(doc))
        scene_ms = max(0.0, (perf_logic.median(scene_runs) - baseline) * 1000.0)

        return perf_logic.finish_scan(entries, baseline, scene_ms)

    def select(self, doc, adapter, tree, payload) -> dict:
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


AUDIT = CinemaPerfAudit()
