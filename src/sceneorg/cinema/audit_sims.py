from __future__ import annotations

import c4d

from ..core import sims_logic

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


def _resolve_ids(specs):
    out = {}
    for tid, kind, label, group in specs:
        if isinstance(tid, int):
            out.setdefault(tid, (kind, label, group))
    return out


TAG_BY_ID = _resolve_ids(TAG_SPECS)
OBJECT_BY_ID = _resolve_ids(OBJECT_SPECS)


def _enable_param(kind):
    for name in ENABLE_PARAMS.get(kind, ()):
        pid = getattr(c4d, name, None)
        if pid is not None:
            return pid
    return None


def _read_enabled(carrier, kind):
    pid = _enable_param(kind)
    if pid is None:
        return None
    try:
        return bool(carrier[pid])
    except Exception:
        return None


def _scan(doc, adapter, tree, progress=None):
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
        obj_spec = OBJECT_BY_ID.get(otype)
        if obj_spec is not None:
            kind, label, group = obj_spec
            hit = sims_logic.SimHit(
                guid=guid, object=obj_name, carrier="object", kind=kind,
                label=label, enabled=_read_enabled(op, kind), hidden=hidden)
            object_hits.append((hit, group))

        try:
            tags = op.GetTags()
        except Exception:
            tags = []
        for tag in tags:
            try:
                ttype = tag.GetType()
            except Exception:
                continue
            spec = TAG_BY_ID.get(ttype)
            if spec is None:
                continue
            kind, label, group = spec
            if group == "cache":
                cache_present = True
                object_hits.append((sims_logic.SimHit(
                    guid=guid, object=obj_name, carrier="tag", kind=kind,
                    label=label, enabled=None, cached=True, hidden=hidden), group))
            else:
                object_hits.append((sims_logic.SimHit(
                    guid=guid, object=obj_name, carrier="tag", kind=kind,
                    label=label, enabled=_read_enabled(tag, kind),
                    hidden=hidden), group))

        for hit, group in object_hits:
            if group == "sim" and hit.kind in SIM_KINDS:
                hit.cached = True if cache_present else False
            hits.append(hit)

    return hits


def _select(doc, adapter, guids):
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


def _set_enabled(doc, adapter, guids, kind, enabled):
    pid = _enable_param(kind)
    applied = 0
    skipped = 0
    if pid is None:
        return 0, len(guids)

    doc.StartUndo()
    for guid in guids:
        op = adapter._by_guid.get(guid)
        if op is None:
            skipped += 1
            continue
        target = None
        try:
            for tag in op.GetTags():
                spec = TAG_BY_ID.get(tag.GetType())
                if spec is not None and spec[0] == kind:
                    target = tag
                    break
        except Exception:
            target = None
        if target is None:
            spec = OBJECT_BY_ID.get(op.GetType() if hasattr(op, "GetType") else None)
            if spec is not None and spec[0] == kind:
                target = op
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


def handle(op, payload, doc, adapter, tree, progress=None):
    if op == "sims_scan":
        hits = _scan(doc, adapter, tree, progress=progress)
        return sims_logic.scan_result(hits)

    if op == "sims_select":
        guids = payload.get("guids")
        if guids is None:
            kind = str(payload.get("kind") or "")
            hits = _scan(doc, adapter, tree, progress=progress)
            guids = [h.guid for h in hits if h.kind == kind]
        selected = _select(doc, adapter, [int(g) for g in guids])
        return {"ok": True, "selected": selected}

    if op == "sims_set_enabled":
        guids = [int(g) for g in (payload.get("guids") or [])]
        kind = str(payload.get("kind") or "")
        enabled = bool(payload.get("enabled"))
        applied, skipped = _set_enabled(doc, adapter, guids, kind, enabled)
        return {"ok": True, "applied": applied, "skipped": skipped}

    return {"error": "unknown sims op: %s" % op}
