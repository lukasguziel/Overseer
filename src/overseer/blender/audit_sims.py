"""Simulations audit for Blender - physics (Cloth, Soft Body, Rigid Body,
Fluid/Mantaflow, Dynamic Paint) + particle systems, with bake/cache state.
STUB: implemented by a dedicated subagent.

Reference: cinema/audit_sims.py. Distinguish sim kinds from cache kinds; flag
whether baked (``point_cache.is_baked``). Ops: sims_scan, sims_select,
sims_set_enabled. Mirror shapes.
"""
from __future__ import annotations

_PHYSICS_MODIFIER_TYPES = {
    "CLOTH", "SOFT_BODY", "DYNAMIC_PAINT", "FLUID", "COLLISION",
    "PARTICLE_SYSTEM", "FLUID_SIMULATION", "SMOKE",
}


def has_any(adapter, tree) -> bool:
    for node in tree.walk():
        obj = adapter._by_guid.get(node.guid)
        if obj is None:
            continue
        try:
            if obj.rigid_body is not None:
                return True
            for m in obj.modifiers:
                if m.type in _PHYSICS_MODIFIER_TYPES:
                    return True
        except Exception:
            continue
    return False


def handle(op, payload, doc, adapter, tree, progress):
    if op == "sims_scan":
        return {"ok": True, "sims": [], "summary": {}}
    return {"error": "unknown sims op: %s" % op}
