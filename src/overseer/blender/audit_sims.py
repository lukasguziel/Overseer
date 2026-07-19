from __future__ import annotations

from ..core import sims_logic


def has_any(adapter, tree) -> bool:
    for node in tree.walk():
        obj = adapter._by_guid.get(node.guid)
        if obj is None:
            continue
        try:
            if getattr(obj, "rigid_body", None) is not None:
                return True
        except Exception:
            pass
        try:
            mods = list(obj.modifiers)
        except Exception:
            mods = []
        for m in mods:
            if _modifier_sim(m) is not None:
                return True
    return False


def _emit(progress, phase, cur, tot, detail):
    if progress is None:
        return
    try:
        progress(phase, cur, tot, detail)
    except Exception:
        pass


def _pc_baked(pc):
    if pc is None:
        return None
    try:
        return bool(pc.is_baked)
    except Exception:
        return None


def _dynpaint_baked(m):
    canvas = getattr(m, "canvas_settings", None)
    if canvas is None:
        return None
    try:
        surfaces = list(canvas.canvas_surfaces)
    except Exception:
        return None
    states = [_pc_baked(getattr(s, "point_cache", None)) for s in surfaces]
    states = [s for s in states if s is not None]
    if not states:
        return None
    return any(states)


def _fluid_spec(m):
    try:
        ftype = m.fluid_type
    except Exception:
        ftype = ""
    if ftype == "DOMAIN":
        ds = getattr(m, "domain_settings", None)
        cached = None
        if ds is not None:
            baked = getattr(ds, "has_cache_baked_data", None)
            if baked is None:
                cached = _pc_baked(getattr(ds, "point_cache", None))
            else:
                try:
                    cached = bool(baked)
                except Exception:
                    cached = None
        return "fluid", "Fluid Domain", cached
    if ftype == "FLOW":
        return "fluid", "Fluid Flow", None
    if ftype == "EFFECTOR":
        return "collider", "Fluid Effector", None
    return "fluid", "Fluid", None


def _particle_spec(m):
    psys = getattr(m, "particle_system", None)
    settings = getattr(psys, "settings", None) if psys is not None else None
    ptype = getattr(settings, "type", "EMITTER") if settings is not None else "EMITTER"
    pc = getattr(psys, "point_cache", None) if psys is not None else None
    if ptype == "HAIR":
        dyn = bool(getattr(settings, "use_hair_dynamics", False)) if settings else False
        return "hair", "Hair", (_pc_baked(pc) if dyn else None)
    return "particle", "Particle System", _pc_baked(pc)


def _modifier_sim(m):
    try:
        mtype = m.type
    except Exception:
        return None
    if mtype == "CLOTH":
        return "cloth", "Cloth", _pc_baked(getattr(m, "point_cache", None))
    if mtype == "SOFT_BODY":
        return "softbody", "Soft Body", _pc_baked(getattr(m, "point_cache", None))
    if mtype == "COLLISION":
        return "collider", "Collision", None
    if mtype == "DYNAMIC_PAINT":
        return "dynamicpaint", "Dynamic Paint", _dynpaint_baked(m)
    if mtype == "FLUID":
        return _fluid_spec(m)
    if mtype == "PARTICLE_SYSTEM":
        return _particle_spec(m)
    return None


def _rigidbody_world_baked(doc):
    try:
        world = doc.scene.rigidbody_world
    except Exception:
        return None
    if world is None:
        return None
    return _pc_baked(getattr(world, "point_cache", None))


def _object_sims(obj, guid, name, hidden, world_baked):
    out = []

    try:
        rb = getattr(obj, "rigid_body", None)
    except Exception:
        rb = None
    if rb is not None:
        try:
            enabled = bool(rb.enabled)
        except Exception:
            enabled = None
        hit = sims_logic.SimHit(
            guid=guid, object=name, carrier="object", kind="rigidbody",
            label="Rigid Body", enabled=enabled, cached=world_baked,
            hidden=hidden)
        hit.index = -1
        out.append(hit)

    try:
        mods = list(obj.modifiers)
    except Exception:
        mods = []
    for i, m in enumerate(mods):
        spec = _modifier_sim(m)
        if spec is None:
            continue
        kind, label, cached = spec
        try:
            enabled = bool(getattr(m, "show_viewport", False)
                           or getattr(m, "show_render", False))
        except Exception:
            enabled = None
        hit = sims_logic.SimHit(
            guid=guid, object=name, carrier="modifier", kind=kind,
            label=label, enabled=enabled, cached=cached, hidden=hidden)
        hit.index = i
        out.append(hit)

    return out


def _scan(doc, adapter, tree, progress=None):
    node_by_guid = {n.guid: n for n in tree.walk()}
    items = list(adapter._by_guid.items())
    total = len(items)
    world_baked = _rigidbody_world_baked(doc)

    hits = []
    for idx, (guid, obj) in enumerate(items):
        if idx % 100 == 0:
            _emit(progress, "Scanning simulations", idx, total, "")
        node = node_by_guid.get(guid)
        if node is None:
            continue
        try:
            hits.extend(_object_sims(obj, guid, node.name, not node.visible,
                                     world_baked))
        except Exception:
            continue
    return hits


def _result(hits):
    dicts = []
    for hit in hits:
        d = hit.to_dict()
        d["index"] = getattr(hit, "index", -1)
        dicts.append(d)
    findings = {
        "active_hidden": [d for h, d in zip(hits, dicts)
                          if sims_logic.is_active_hidden(h)],
        "unbaked": [d for h, d in zip(hits, dicts)
                    if sims_logic.is_unbaked(h)],
        "disabled_leftovers": [d for h, d in zip(hits, dicts)
                               if sims_logic.is_disabled_leftover(h)],
    }
    return {
        "ok": True,
        "hits": dicts,
        "findings": findings,
        "summary": sims_logic.summarize(hits),
    }


def _dedupe_guids(guids):
    seen = set()
    ordered = []
    for g in guids:
        try:
            gi = int(g)
        except Exception:
            continue
        if gi not in seen:
            seen.add(gi)
            ordered.append(gi)
    return ordered


def _select(doc, adapter, guids):
    objs = [adapter._by_guid.get(g) for g in guids]
    objs = [o for o in objs if o is not None]

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
    return selected


def _apply_enabled(obj, kind, index, enabled):
    try:
        idx = int(index) if index is not None else -1
    except Exception:
        idx = -1

    if idx < 0:
        if kind != "rigidbody":
            return False
        rb = getattr(obj, "rigid_body", None)
        if rb is None:
            return False
        try:
            rb.enabled = bool(enabled)
            return True
        except Exception:
            return False

    try:
        mods = list(obj.modifiers)
    except Exception:
        return False
    if not (0 <= idx < len(mods)):
        return False
    m = mods[idx]
    spec = _modifier_sim(m)
    if spec is None or spec[0] != kind:
        return False
    val = bool(enabled)
    applied = False
    try:
        m.show_viewport = val
        applied = True
    except Exception:
        pass
    try:
        m.show_render = val
        applied = True
    except Exception:
        pass
    return applied


def _set_enabled(doc, adapter, targets, enabled):
    applied = 0
    skipped = 0
    for guid, kind, index in targets:
        obj = adapter._by_guid.get(guid)
        if obj is None:
            skipped += 1
            continue
        if _apply_enabled(obj, kind, index, enabled):
            applied += 1
        else:
            skipped += 1
    if applied:
        doc.undo_push("Overseer: toggle simulations")
        doc.tag_redraw()
    return applied, skipped


def handle(op, payload, doc, adapter, tree, progress=None):
    if op == "sims_scan":
        hits = _scan(doc, adapter, tree, progress=progress)
        return _result(hits)

    if op == "sims_select":
        guids = payload.get("guids")
        if guids is None:
            kind = str(payload.get("kind") or "")
            hits = _scan(doc, adapter, tree, progress=progress)
            guids = [h.guid for h in hits if h.kind == kind]
        selected = _select(doc, adapter, _dedupe_guids(guids))
        return {"ok": True, "selected": selected}

    if op == "sims_set_enabled":
        enabled = bool(payload.get("enabled"))
        targets = []
        for t in payload.get("targets") or []:
            try:
                targets.append(
                    (int(t.get("guid")), str(t.get("kind") or ""), t.get("index")))
            except Exception:
                continue
        applied, skipped = _set_enabled(doc, adapter, targets, enabled)
        return {"ok": True, "applied": applied, "skipped": skipped}

    return {"error": "unknown sims op: %s" % op}
