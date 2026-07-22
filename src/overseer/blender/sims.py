from __future__ import annotations

from ..core.sims import logic as sims_logic
from ..core.sims.audit import SimsAudit


class BlenderSimsAudit(SimsAudit):
    """Simulation audit (Blender host). Rigid bodies live on the object; every
    other sim (cloth, soft body, collision, dynamic paint, fluid, particles,
    hair) is a modifier. Bake state comes from the relevant point cache."""

    def has_any(self, adapter, tree) -> bool:
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
                if self._modifier_sim(m) is not None:
                    return True
        return False

    def _emit(self, progress, phase, cur, tot, detail):
        if progress is None:
            return
        try:
            progress(phase, cur, tot, detail)
        except Exception:
            pass

    def _pc_baked(self, pc):
        if pc is None:
            return None
        try:
            return bool(pc.is_baked)
        except Exception:
            return None

    def _dynpaint_baked(self, m):
        canvas = getattr(m, "canvas_settings", None)
        if canvas is None:
            return None
        try:
            surfaces = list(canvas.canvas_surfaces)
        except Exception:
            return None
        states = [self._pc_baked(getattr(s, "point_cache", None)) for s in surfaces]
        states = [s for s in states if s is not None]
        if not states:
            return None
        return any(states)

    def _fluid_spec(self, m):
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
                    cached = self._pc_baked(getattr(ds, "point_cache", None))
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

    def _particle_spec(self, m):
        psys = getattr(m, "particle_system", None)
        settings = getattr(psys, "settings", None) if psys is not None else None
        ptype = getattr(settings, "type", "EMITTER") if settings is not None else "EMITTER"
        pc = getattr(psys, "point_cache", None) if psys is not None else None
        if ptype == "HAIR":
            dyn = bool(getattr(settings, "use_hair_dynamics", False)) if settings else False
            return "hair", "Hair", (self._pc_baked(pc) if dyn else None)
        return "particle", "Particle System", self._pc_baked(pc)

    def _modifier_sim(self, m):
        try:
            mtype = m.type
        except Exception:
            return None
        if mtype == "CLOTH":
            return "cloth", "Cloth", self._pc_baked(getattr(m, "point_cache", None))
        if mtype == "SOFT_BODY":
            return "softbody", "Soft Body", self._pc_baked(getattr(m, "point_cache", None))
        if mtype == "COLLISION":
            return "collider", "Collision", None
        if mtype == "DYNAMIC_PAINT":
            return "dynamicpaint", "Dynamic Paint", self._dynpaint_baked(m)
        if mtype == "FLUID":
            return self._fluid_spec(m)
        if mtype == "PARTICLE_SYSTEM":
            return self._particle_spec(m)
        return None

    def _rigidbody_world_baked(self, doc):
        try:
            world = doc.scene.rigidbody_world
        except Exception:
            return None
        if world is None:
            return None
        return self._pc_baked(getattr(world, "point_cache", None))

    def _object_sims(self, obj, guid, name, hidden, world_baked):
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
            spec = self._modifier_sim(m)
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

    def collect(self, doc, adapter, tree, progress) -> list:
        node_by_guid = {n.guid: n for n in tree.walk()}
        items = list(adapter._by_guid.items())
        total = len(items)
        world_baked = self._rigidbody_world_baked(doc)

        hits = []
        for idx, (guid, obj) in enumerate(items):
            if idx % 100 == 0:
                self._emit(progress, "Scanning simulations", idx, total, "")
            node = node_by_guid.get(guid)
            if node is None:
                continue
            try:
                hits.extend(self._object_sims(obj, guid, node.name, not node.visible,
                                              world_baked))
            except Exception:
                continue
        return hits

    def _dedupe_guids(self, guids):
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

    def _select(self, doc, adapter, guids):
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

    def _apply_enabled(self, obj, kind, index, enabled):
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
        spec = self._modifier_sim(m)
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

    def _set_enabled(self, doc, adapter, targets, enabled):
        applied = 0
        skipped = 0
        for guid, kind, index in targets:
            obj = adapter._by_guid.get(guid)
            if obj is None:
                skipped += 1
                continue
            if self._apply_enabled(obj, kind, index, enabled):
                applied += 1
            else:
                skipped += 1
        if applied:
            doc.undo_push("Overseer: toggle simulations")
            doc.tag_redraw()
        return applied, skipped

    def select(self, doc, adapter, payload) -> dict:
        guids = payload.get("guids")
        if guids is None:
            kind = str(payload.get("kind") or "")
            hits = self.collect(doc, adapter, adapter.build_tree(), None)
            guids = [h.guid for h in hits if h.kind == kind]
        selected = self._select(doc, adapter, self._dedupe_guids(guids))
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


AUDIT = BlenderSimsAudit()
