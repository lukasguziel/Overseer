from __future__ import annotations

import c4d

from ..core import sims_logic
from ..core.hostapi.audits import SimsAudit

TAG_SPECS = [
    (180000102, "dynamics", "Dynamics Body", "sim"),
    (100004020, "cloth", "Cloth", "sim"),
    (getattr(c4d, "Tcloth", None), "cloth", "Cloth", "sim"),
    (180000103, "collider", "Collider", "sim"),
    (100004021, "collider", "Cloth Collider", "sim"),
    (getattr(c4d, "Tclothbelt", None), "cloth", "Cloth Belt", "sim"),
    (getattr(c4d, "Tpyroobject", None) or 1059247, "pyro", "Pyro", "sim"),
    (getattr(c4d, "Tmgcache", None) or 1019337, "mocache", "MoGraph Cache", "cache"),
    (getattr(c4d, "Tpointcache", None) or 1021302, "pointcache", "Point Cache", "cache"),
]

OBJECT_SPECS = [
    (getattr(c4d, "Oparticle", None), "particle", "Particle Emitter", "sim"),
    (getattr(c4d, "Othinkingparticles", None), "tp", "Thinking Particles", "sim"),
    (getattr(c4d, "Ohair", None), "hair", "Hair", "sim"),
    (getattr(c4d, "Opyrooutput", None), "pyro_out", "Pyro Output", "sim"),
]

SIM_KINDS = {"dynamics", "cloth", "collider", "pyro", "particle", "tp", "hair", "pyro_out"}
CACHE_KINDS = {"mocache", "pointcache"}

ENABLE_PARAMS = {
    "dynamics": ("RIGID_BODY_ENABLED",),
    "collider": ("RIGID_BODY_ENABLED",),
    "cloth": ("CLOTH_ENABLE", "CLOTH_ENABLED"),
    "particle": (),
    "hair": (),
}


class CinemaSimsAudit(SimsAudit):
    """Simulation audit (Cinema 4D host). Sims are carried either by a tag
    (Dynamics/Cloth/Collider/Pyro, and cache tags) or by an object type
    (particle emitter, Thinking Particles, Hair, Pyro Output). Cache tags on an
    object mark its sims as baked."""

    def __init__(self):
        self.TAG_BY_ID = self._resolve_ids(TAG_SPECS)
        self.OBJECT_BY_ID = self._resolve_ids(OBJECT_SPECS)

    @staticmethod
    def _resolve_ids(specs):
        out = {}
        for tid, kind, label, group in specs:
            if isinstance(tid, int):
                out.setdefault(tid, (kind, label, group))
        return out

    def _enable_param(self, kind):
        for name in ENABLE_PARAMS.get(kind, ()):
            pid = getattr(c4d, name, None)
            if pid is not None:
                return pid
        return None

    def _read_enabled(self, carrier, kind):
        pid = self._enable_param(kind)
        if pid is None:
            return None
        try:
            return bool(carrier[pid])
        except Exception:
            return None

    def has_any(self, adapter, tree) -> bool:
        for _guid, op in adapter._by_guid.items():
            try:
                if self.OBJECT_BY_ID.get(op.GetType()) is not None:
                    return True
                for tag in op.GetTags():
                    if self.TAG_BY_ID.get(tag.GetType()) is not None:
                        return True
            except Exception:
                continue
        return False

    def collect(self, doc, adapter, tree, progress) -> list:
        node_by_guid = {n.guid: n for n in tree.walk()}
        items = list(adapter._by_guid.items())
        total = len(items)

        hits = []
        for idx, (guid, op) in enumerate(items):
            if progress and idx % 100 == 0:
                progress("Scanning simulations", idx, total, "")
            node = node_by_guid.get(guid)
            if node is None:
                continue
            obj_name = node.name
            hidden = not node.visible

            object_hits = []
            cache_present = False

            try:
                otype = op.GetType()
            except Exception:
                otype = None
            obj_spec = self.OBJECT_BY_ID.get(otype)
            if obj_spec is not None:
                kind, label, group = obj_spec
                hit = sims_logic.SimHit(
                    guid=guid, object=obj_name, carrier="object", kind=kind,
                    label=label, enabled=self._read_enabled(op, kind), hidden=hidden)
                hit.index = -1
                object_hits.append((hit, group))

            try:
                tags = op.GetTags()
            except Exception:
                tags = []
            for tidx, tag in enumerate(tags):
                try:
                    ttype = tag.GetType()
                except Exception:
                    continue
                spec = self.TAG_BY_ID.get(ttype)
                if spec is None:
                    continue
                kind, label, group = spec
                if group == "cache":
                    cache_present = True
                    hit = sims_logic.SimHit(
                        guid=guid, object=obj_name, carrier="tag", kind=kind,
                        label=label, enabled=None, cached=True, hidden=hidden)
                else:
                    hit = sims_logic.SimHit(
                        guid=guid, object=obj_name, carrier="tag", kind=kind,
                        label=label, enabled=self._read_enabled(tag, kind),
                        hidden=hidden)
                hit.index = tidx
                object_hits.append((hit, group))

            for hit, group in object_hits:
                if group == "sim" and hit.kind in SIM_KINDS:
                    hit.cached = True if cache_present else False
                hits.append(hit)

        return hits

    def _select(self, doc, adapter, guids):
        selected = 0
        first = True
        for guid in guids:
            op = adapter._by_guid.get(guid)
            if op is None:
                continue
            try:
                doc.SetActiveObject(
                    op, c4d.SELECTION_NEW if first else c4d.SELECTION_ADD)
                selected += 1
                first = False
            except Exception:
                continue
        c4d.EventAdd()
        return selected

    def _target_for(self, op, kind, index):
        if index is not None and index >= 0:
            try:
                tags = op.GetTags()
            except Exception:
                tags = []
            if 0 <= index < len(tags):
                tag = tags[index]
                try:
                    spec = self.TAG_BY_ID.get(tag.GetType())
                except Exception:
                    spec = None
                if spec is not None and spec[0] == kind:
                    return tag
            return None
        spec = self.OBJECT_BY_ID.get(op.GetType() if hasattr(op, "GetType") else None)
        if spec is not None and spec[0] == kind:
            return op
        return None

    def _set_enabled(self, doc, adapter, targets, enabled):
        applied = 0
        skipped = 0

        doc.StartUndo()
        for guid, kind, index in targets:
            pid = self._enable_param(kind)
            op = adapter._by_guid.get(guid)
            if pid is None or op is None:
                skipped += 1
                continue
            target = self._target_for(op, kind, index)
            if target is None:
                skipped += 1
                continue
            try:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, target)
                target[pid] = bool(enabled)
                applied += 1
            except Exception:
                skipped += 1
        doc.EndUndo()
        c4d.EventAdd()
        return applied, skipped

    def select(self, doc, adapter, payload) -> dict:
        guids = payload.get("guids")
        if guids is None:
            kind = str(payload.get("kind") or "")
            hits = self.collect(doc, adapter, adapter.build_tree(), None)
            guids = [h.guid for h in hits if h.kind == kind]
        selected = self._select(doc, adapter, [int(g) for g in guids])
        return {"ok": True, "selected": selected}

    def set_enabled(self, doc, adapter, payload) -> dict:
        enabled = bool(payload.get("enabled"))
        targets = []
        for t in payload.get("targets") or []:
            try:
                targets.append(
                    (int(t.get("guid")), str(t.get("kind") or ""), t.get("index")))
            except Exception:
                continue
        applied, skipped = self._set_enabled(doc, adapter, targets, enabled)
        return {"ok": True, "applied": applied, "skipped": skipped}


AUDIT = CinemaSimsAudit()
