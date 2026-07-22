from __future__ import annotations

import time

from ..core.perf import logic as perf_logic
from ..core.perf.audit import PerfAudit

_REPEATS = 3


class BlenderPerfAudit(PerfAudit):
    """Viewport rebuild-cost audit (Blender host)."""

    def _emit(self, progress, phase, cur, tot, detail):
        if progress is None:
            return
        try:
            progress(phase, cur, tot, detail)
        except Exception:
            pass

    def _is_candidate(self, obj) -> bool:
        try:
            mods = getattr(obj, "modifiers", None)
            if mods and len(mods) > 0:
                return True
            gp = getattr(obj, "grease_pencil_modifiers", None)
            return bool(gp) and len(gp) > 0
        except Exception:
            return False

    def _candidates(self, adapter, tree):
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

    def _type_label(self, obj) -> str:
        try:
            mods = list(obj.modifiers)
        except Exception:
            mods = []
        names = []
        for m in mods:
            try:
                label = m.bl_rna.name or m.type.replace("_", " ").title()
            except Exception:
                try:
                    label = m.type.replace("_", " ").title()
                except Exception:
                    label = "Modifier"
            names.append(label)
        if not names:
            try:
                return obj.type.replace("_", " ").title()
            except Exception:
                return "Object"
        if len(names) == 1:
            return names[0]
        return "%s +%d" % (names[0], len(names) - 1)

    def _depsgraph(self, adapter):
        try:
            return adapter.bpy.context.evaluated_depsgraph_get()
        except Exception:
            return None

    def _update(self, dg) -> float:
        if dg is None:
            return 0.0
        t0 = time.perf_counter()
        try:
            dg.update()
        except Exception:
            pass
        return time.perf_counter() - t0

    def _tag(self, obj) -> None:
        try:
            obj.update_tag(refresh={"OBJECT", "DATA"})
        except Exception:
            try:
                obj.update_tag()
            except Exception:
                pass

    def _empty_result(self):
        return {"ok": True, "entries": [],
                "summary": {"total": 0, "measured": 0, "total_ms": 0.0,
                            "heavy": 0, "slowest": "", "slowest_ms": 0.0,
                            "slowest_share": 0.0, "scene_ms": 0.0,
                            "overlap": 0.0},
                "baseline_ms": 0.0, "scene_ms": 0.0}

    def scan(self, doc, adapter, tree, payload, progress) -> dict:
        try:
            cands = self._candidates(adapter, tree)
            if not cands:
                return self._empty_result()

            repeats = max(1, min(5, int(payload.get("repeats") or _REPEATS)))
            dg = self._depsgraph(adapter)
            if dg is None:
                return self._empty_result()

            self._update(dg)
            baseline = perf_logic.median([self._update(dg) for _ in range(repeats)])

            entries = []
            total = len(cands)
            for i, (node, obj) in enumerate(cands):
                self._emit(progress, "Measuring rebuild times", i, total, node.name)
                samples = []
                for _ in range(repeats):
                    self._tag(obj)
                    samples.append(self._update(dg))
                if not samples:
                    continue
                entries.append({
                    "guid": node.guid,
                    "name": node.name,
                    "type": self._type_label(obj),
                    "ms": max(0.0, (perf_logic.median(samples) - baseline) * 1000.0),
                    "jitter_ms": perf_logic.jitter(samples) * 1000.0,
                    "runs": len(samples),
                    "polygons": getattr(node, "poly_count", 0) or 0,
                })

            self._emit(progress, "Measuring rebuild times", total, total, "full scene")
            scene_runs = []
            for _ in range(repeats):
                for _node, obj in cands:
                    self._tag(obj)
                scene_runs.append(self._update(dg))
            scene_ms = max(0.0, (perf_logic.median(scene_runs) - baseline) * 1000.0)

            result = perf_logic.rank(entries)
            result["ok"] = True
            result["baseline_ms"] = baseline * 1000.0
            result["scene_ms"] = scene_ms
            result["summary"]["scene_ms"] = scene_ms
            result["summary"]["overlap"] = perf_logic.overlap_ratio(
                result["summary"]["total_ms"], scene_ms)
            return result
        except Exception as ex:  # noqa: BLE001
            return {"error": "perf scan failed: %s" % ex}

    def select(self, doc, adapter, tree, payload) -> dict:
        guids = payload.get("guids") or []
        objs = []
        seen = set()
        for g in guids:
            try:
                gi = int(g)
            except Exception:
                continue
            if gi in seen:
                continue
            seen.add(gi)
            obj = adapter._by_guid.get(gi)
            if obj is not None:
                objs.append(obj)

        try:
            for o in doc.selected_objects():
                o.select_set(False)
        except Exception:
            pass

        selected = 0
        for o in objs:
            try:
                o.select_set(True)
                adapter.bpy.context.view_layer.objects.active = o
                selected += 1
            except Exception:
                continue
        doc.tag_redraw()
        return {"ok": True, "selected": selected}


AUDIT = BlenderPerfAudit()
