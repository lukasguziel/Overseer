"""Tags audit for Blender - there are no C4D "tags"; we audit object
attachments: modifiers, constraints, and mesh smoothing (the Phong analog).

The Blender twin of ``cinema/audit_tags.py``. Blender has no "tags", so a
"type" row is one attachment KIND: a modifier type (grouped), a constraint
type, or "Shade Smooth" (the smoothing analog of a Phong tag). Kind ids are
synthetic - a stable integer hashed from the kind string - because Blender
kinds are strings and the frontend only needs an opaque, unique selector.

Result shapes mirror the C4D audit key-for-key so the frozen ``TagsTab``
renders unchanged:

- ``types``: ``[{type_id, label, count, objects:[{guid, name, tags:[{name}]}]}]``
- ``findings.missing_phong``: meshes that are NOT shade-smooth
- ``findings.duplicate_material_tags``: meshes with duplicate slots pointing at
  the SAME material
- ``findings.phong_angles``: distribution + dominant Auto-Smooth angle (degrees)
- ``summary``: ``total_tags`` / ``tag_types`` / ``missing_phong`` /
  ``duplicate_material_tags``

Ops: tags_scan, tags_add_phong, tags_set_phong_angle, tags_delete_duplicates,
tags_select. Every mutation ends with ONE ``doc.undo_push``.

No top-level ``import bpy`` - the bpy module is reached through ``adapter.bpy``
so the rest of the package stays importable without Blender (CI).
"""
from __future__ import annotations

import math
import zlib

from ..core.tags_logic import (
    DEFAULT_PHONG_ANGLE_DEG,
    deg_from_rad,
    dominant_angle,
)

# Modifier names that Blender 4.1+ adds for "Shade Auto Smooth" - a Geometry
# Nodes modifier, not a mesh flag. Matched case-insensitively.
_SMOOTH_BY_ANGLE = "smooth by angle"

# Candidate socket identifiers for the Smooth by Angle angle input, tried in
# order before falling back to introspecting the node group interface.
_ANGLE_SOCKETS = ("Input_1", "Socket_1", "Angle")


# ---------------------------------------------------------------------------
# small defensive readers
# ---------------------------------------------------------------------------
def _safe_iter(obj, attr) -> list:
    try:
        return list(getattr(obj, attr))
    except Exception:
        return []


def _attr(o, name, default):
    try:
        v = getattr(o, name)
        return v if v is not None else default
    except Exception:
        return default


def _is_mesh(obj) -> bool:
    try:
        return obj.type == "MESH"
    except Exception:
        return False


def _mesh_data(obj):
    try:
        data = obj.data
    except Exception:
        return None
    if data is not None and hasattr(data, "polygons"):
        return data
    return None


def _kind_id(kind: str) -> int:
    """Stable synthetic int id for a kind string (opaque to the frontend)."""
    try:
        return zlib.crc32(kind.encode("utf-8")) & 0x7FFFFFFF
    except Exception:
        return 0


def _modifier_label(mod) -> str:
    try:
        nm = mod.bl_rna.name
        if nm:
            return nm
    except Exception:
        pass
    return _attr(mod, "type", "Modifier").replace("_", " ").title()


def _constraint_label(con) -> str:
    base = ""
    try:
        base = con.bl_rna.name or ""
    except Exception:
        base = ""
    if not base:
        base = _attr(con, "type", "Constraint").replace("_", " ").title()
    return base + " (constraint)"


def _mat_key(mat) -> str:
    """Datablock identity: two slots pointing at the SAME material share it."""
    try:
        return mat.name_full
    except Exception:
        try:
            return "id:%d" % id(mat)
        except Exception:
            return "?"


def _mat_name(mat) -> str:
    try:
        return mat.name or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# mesh smoothing (the Phong analog)
# ---------------------------------------------------------------------------
def _smooth_by_angle_modifier(obj):
    """The 4.1+ "Smooth by Angle" Geometry Nodes modifier, if present."""
    for mod in _safe_iter(obj, "modifiers"):
        try:
            if _SMOOTH_BY_ANGLE in (mod.name or "").lower():
                return mod
        except Exception:
            pass
        try:
            ng = getattr(mod, "node_group", None)
            if ng is not None and _SMOOTH_BY_ANGLE in (ng.name or "").lower():
                return mod
        except Exception:
            continue
    return None


def _read_modifier_angle(mod):
    """Best-effort read of the Smooth by Angle angle input (radians)."""
    for ident in _ANGLE_SOCKETS:
        try:
            v = mod[ident]
            if isinstance(v, (int, float)):
                return float(v)
        except Exception:
            continue
    try:
        ng = mod.node_group
        for item in ng.interface.items_tree:
            if (getattr(item, "in_out", "") == "INPUT"
                    and getattr(item, "subtype", "") == "ANGLE"):
                v = mod[item.identifier]
                if isinstance(v, (int, float)):
                    return float(v)
    except Exception:
        pass
    return None


def _write_modifier_angle(mod, radians: float) -> bool:
    for ident in _ANGLE_SOCKETS:
        try:
            mod[ident] = radians
            return True
        except Exception:
            continue
    try:
        ng = mod.node_group
        for item in ng.interface.items_tree:
            if (getattr(item, "in_out", "") == "INPUT"
                    and getattr(item, "subtype", "") == "ANGLE"):
                mod[item.identifier] = radians
                return True
    except Exception:
        pass
    return False


def _smooth_state(obj) -> dict:
    """(smooth, auto, angle_deg) for a mesh object.

    ``smooth`` - is it shade-smooth at all (the "has a Phong tag" analog).
    ``auto``   - does it carry Auto-Smooth (legacy flag or 4.1+ modifier);
                 only these contribute an angle to the distribution.
    ``angle_deg`` - the Auto-Smooth angle in degrees, when determinable.
    """
    state = {"smooth": False, "auto": False, "angle_deg": None}
    mesh = _mesh_data(obj)
    if mesh is None:
        return state

    # Whole-object shade-smooth is uniform in practice; sampling the first
    # polygon keeps this O(1) on the multi-million-poly production scene.
    try:
        polys = mesh.polygons
        if len(polys) and polys[0].use_smooth:
            state["smooth"] = True
    except Exception:
        pass

    # Legacy (<=4.0): the mesh carries the auto-smooth flag + angle directly.
    try:
        if getattr(mesh, "use_auto_smooth", False):
            state["auto"] = True
            state["smooth"] = True
            ang = getattr(mesh, "auto_smooth_angle", None)
            if ang is not None:
                state["angle_deg"] = deg_from_rad(float(ang))
    except Exception:
        pass

    # 4.1+: Auto-Smooth is a "Smooth by Angle" Geometry Nodes modifier.
    if not state["auto"]:
        mod = _smooth_by_angle_modifier(obj)
        if mod is not None:
            state["auto"] = True
            state["smooth"] = True
            rad = _read_modifier_angle(mod)
            if rad is not None:
                state["angle_deg"] = deg_from_rad(rad)

    return state


def _apply_smooth(obj, radians: float, bpy) -> bool:
    """Shade-smooth a mesh and enable Auto-Smooth at ``radians``."""
    mesh = _mesh_data(obj)
    if mesh is None:
        return False
    ok = False
    # Shade smooth via polygon flags - version-agnostic, needs no operator.
    try:
        n = len(mesh.polygons)
        if n:
            mesh.polygons.foreach_set("use_smooth", [True] * n)
            try:
                mesh.update()
            except Exception:
                pass
            ok = True
    except Exception:
        pass
    # Auto-Smooth: prefer the direct data API (<=4.0), else the 4.1+ operator.
    try:
        if hasattr(mesh, "use_auto_smooth"):
            mesh.use_auto_smooth = True
            try:
                mesh.auto_smooth_angle = radians
            except Exception:
                pass
            ok = True
        elif _op_shade_auto_smooth(obj, radians, bpy):
            ok = True
    except Exception:
        pass
    return ok


def _op_shade_auto_smooth(obj, radians: float, bpy) -> bool:
    """4.1+ Auto-Smooth via operator (adds/updates the modifier)."""
    try:
        with bpy.context.temp_override(
                object=obj, active_object=obj,
                selected_objects=[obj], selected_editable_objects=[obj]):
            bpy.ops.object.shade_auto_smooth(angle=radians)
        return True
    except Exception:
        pass
    # Older signature: shade_smooth carried the auto-smooth args.
    try:
        with bpy.context.temp_override(
                object=obj, active_object=obj,
                selected_objects=[obj], selected_editable_objects=[obj]):
            bpy.ops.object.shade_smooth(
                use_auto_smooth=True, auto_smooth_angle=radians)
        return True
    except Exception:
        return False


def _set_auto_smooth_angle(obj, radians: float, bpy) -> bool:
    """Set the Auto-Smooth angle on a mesh that already has Auto-Smooth."""
    mesh = _mesh_data(obj)
    if mesh is None:
        return False
    if hasattr(mesh, "use_auto_smooth"):
        try:
            mesh.auto_smooth_angle = radians
            mesh.use_auto_smooth = True
            return True
        except Exception:
            return False
    mod = _smooth_by_angle_modifier(obj)
    if mod is None:
        return False
    if _write_modifier_angle(mod, radians):
        try:
            obj.update_tag()
        except Exception:
            pass
        return True
    # Re-running the operator updates the existing modifier in place.
    return _op_shade_auto_smooth(obj, radians, bpy)


# ---------------------------------------------------------------------------
# duplicate material slots
# ---------------------------------------------------------------------------
def _duplicate_material_slots(obj) -> list:
    """[(material_name, count)] for materials filling more than one slot."""
    out: list = []
    seen: dict = {}
    order: list = []
    for slot in _safe_iter(obj, "material_slots"):
        try:
            mat = slot.material
        except Exception:
            mat = None
        if mat is None:
            continue
        key = _mat_key(mat)
        if key in seen:
            seen[key][1] += 1
        else:
            seen[key] = [_mat_name(mat), 1]
            order.append(key)
    for key in order:
        name, count = seen[key]
        if count > 1:
            out.append((name, count))
    return out


def _remove_duplicate_slots(obj, bpy) -> int:
    seen: set = set()
    dup_idx: list = []
    for i, slot in enumerate(_safe_iter(obj, "material_slots")):
        try:
            mat = slot.material
        except Exception:
            mat = None
        if mat is None:
            continue
        key = _mat_key(mat)
        if key in seen:
            dup_idx.append(i)
        else:
            seen.add(key)
    removed = 0
    # High index first so earlier indices stay valid as slots are removed.
    for i in sorted(dup_idx, reverse=True):
        if _remove_slot(obj, i, bpy):
            removed += 1
    return removed


def _remove_slot(obj, index: int, bpy) -> bool:
    try:
        obj.active_material_index = index
        with bpy.context.temp_override(
                object=obj, active_object=obj,
                selected_objects=[obj], selected_editable_objects=[obj]):
            bpy.ops.object.material_slot_remove()
        return True
    except Exception:
        # Fallback: pop from the datablock (operator remaps polygon indices;
        # this path is a best-effort last resort).
        try:
            obj.data.materials.pop(index=index)
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# kind ids for an object (used by tags_select on synthetic type_ids)
# ---------------------------------------------------------------------------
def _object_kind_ids(obj) -> set:
    ids: set = set()
    for mod in _safe_iter(obj, "modifiers"):
        ids.add(_kind_id("mod:" + _attr(mod, "type", "UNKNOWN")))
    for con in _safe_iter(obj, "constraints"):
        ids.add(_kind_id("con:" + _attr(con, "type", "UNKNOWN")))
    if _is_mesh(obj):
        state = _smooth_state(obj)
        if state["smooth"] or state["auto"]:
            ids.add(_kind_id("smooth"))
    return ids


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------
def _add_attachment(types: dict, node_tags: dict, kind: str, label: str,
                    name: str) -> None:
    entry = types.get(kind)
    if entry is None:
        entry = {"type_id": _kind_id(kind), "label": label,
                 "count": 0, "objects": []}
        types[kind] = entry
    entry["count"] += 1
    node_tags.setdefault(kind, []).append({"name": name})


def _scan(doc, adapter, tree, progress) -> dict:
    nodes = list(tree.walk())
    total = len(nodes)

    types: dict = {}
    missing_phong: list = []
    duplicate_material_tags: list = []
    phong_angles: dict = {}
    total_tags = 0

    for i, node in enumerate(nodes):
        if progress and i % 50 == 0:
            progress("Scanning attachments", i, total, node.name)
        obj = adapter._by_guid.get(node.guid)
        if obj is None:
            continue

        node_tags: dict = {}

        for mod in _safe_iter(obj, "modifiers"):
            kind = "mod:" + _attr(mod, "type", "UNKNOWN")
            _add_attachment(types, node_tags, kind, _modifier_label(mod),
                            _attr(mod, "name", ""))
            total_tags += 1

        for con in _safe_iter(obj, "constraints"):
            kind = "con:" + _attr(con, "type", "UNKNOWN")
            _add_attachment(types, node_tags, kind, _constraint_label(con),
                            _attr(con, "name", ""))
            total_tags += 1

        if _is_mesh(obj):
            state = _smooth_state(obj)
            if state["smooth"] or state["auto"]:
                if state["auto"] and state["angle_deg"] is not None:
                    label_name = "Auto-Smooth %g°" % state["angle_deg"]
                elif state["auto"]:
                    label_name = "Auto-Smooth"
                else:
                    label_name = "Smooth"
                _add_attachment(types, node_tags, "smooth", "Shade Smooth",
                                label_name)
                total_tags += 1
                if state["auto"] and state["angle_deg"] is not None:
                    deg = state["angle_deg"]
                    phong_angles[deg] = phong_angles.get(deg, 0) + 1
            else:
                missing_phong.append({"guid": node.guid, "name": node.name})

            for mat_name, count in _duplicate_material_slots(obj):
                duplicate_material_tags.append(
                    {"guid": node.guid, "name": node.name,
                     "material": mat_name, "count": count})

        for kind, refs in node_tags.items():
            types[kind]["objects"].append(
                {"guid": node.guid, "name": node.name, "tags": refs})

    if progress:
        progress("Scanning attachments", total, total, "")

    type_list = sorted(types.values(), key=lambda e: (-e["count"], e["label"]))
    dominant = dominant_angle(phong_angles)
    angle_dist = [{"angle_deg": deg, "count": n}
                  for deg, n in sorted(phong_angles.items())]

    return {
        "ok": True,
        "types": type_list,
        "findings": {
            "missing_phong": missing_phong,
            "duplicate_material_tags": duplicate_material_tags,
            "phong_angles": {
                "distribution": angle_dist,
                "dominant_angle": dominant,
            },
        },
        "summary": {
            "total_tags": total_tags,
            "tag_types": len(type_list),
            "missing_phong": len(missing_phong),
            "duplicate_material_tags": len(duplicate_material_tags),
        },
    }


def _current_phong_angles(adapter, tree) -> dict:
    counts: dict = {}
    for node in tree.walk():
        obj = adapter._by_guid.get(node.guid)
        if obj is None or not _is_mesh(obj):
            continue
        state = _smooth_state(obj)
        if state["auto"] and state["angle_deg"] is not None:
            deg = state["angle_deg"]
            counts[deg] = counts.get(deg, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# mutations
# ---------------------------------------------------------------------------
def _add_phong(doc, adapter, tree, payload) -> dict:
    bpy = adapter.bpy
    guids = payload.get("guids")
    wanted = set(guids) if guids is not None else None
    angle_deg = dominant_angle(_current_phong_angles(adapter, tree))
    if angle_deg is None:
        angle_deg = DEFAULT_PHONG_ANGLE_DEG
    radians = math.radians(float(angle_deg))

    applied = 0
    for node in tree.walk():
        if wanted is not None and node.guid not in wanted:
            continue
        obj = adapter._by_guid.get(node.guid)
        if obj is None or not _is_mesh(obj):
            continue
        state = _smooth_state(obj)
        if state["smooth"] or state["auto"]:
            continue
        if _apply_smooth(obj, radians, bpy):
            applied += 1

    if applied:
        doc.undo_push("Overseer: add auto-smooth")
    doc.tag_redraw()
    return {"ok": True, "applied": applied,
            "angle_deg": round(float(angle_deg), 1)}


def _set_phong_angle(doc, adapter, tree, payload) -> dict:
    bpy = adapter.bpy
    try:
        angle_deg = float(payload.get("angle_deg"))
    except (TypeError, ValueError):
        return {"error": "angle_deg must be a number"}
    radians = math.radians(angle_deg)
    guids = payload.get("guids")
    wanted = set(guids) if guids is not None else None

    applied = 0
    for node in tree.walk():
        if wanted is not None and node.guid not in wanted:
            continue
        obj = adapter._by_guid.get(node.guid)
        if obj is None or not _is_mesh(obj):
            continue
        if not _smooth_state(obj)["auto"]:
            continue
        if _set_auto_smooth_angle(obj, radians, bpy):
            applied += 1

    if applied:
        doc.undo_push("Overseer: set auto-smooth angle")
    doc.tag_redraw()
    return {"ok": True, "applied": applied, "angle_deg": round(angle_deg, 1)}


def _delete_duplicates(doc, adapter, tree, payload) -> dict:
    bpy = adapter.bpy
    guids = payload.get("guids")
    wanted = set(guids) if guids is not None else None

    deleted = 0
    for node in tree.walk():
        if wanted is not None and node.guid not in wanted:
            continue
        obj = adapter._by_guid.get(node.guid)
        if obj is None or not _is_mesh(obj):
            continue
        deleted += _remove_duplicate_slots(obj, bpy)

    if deleted:
        doc.undo_push("Overseer: remove duplicate material slots")
    doc.tag_redraw()
    return {"ok": True, "deleted": deleted}


def _select(doc, adapter, tree, payload) -> dict:
    bpy = adapter.bpy
    guids = payload.get("guids")
    type_ids = payload.get("type_ids")
    if type_ids is None and payload.get("type_id") is not None:
        type_ids = [payload.get("type_id")]

    objs: list = []
    if guids is not None:
        for g in guids:
            o = adapter._by_guid.get(g)
            if o is not None:
                objs.append(o)
    elif type_ids is not None:
        try:
            wanted = {int(t) for t in type_ids}
        except (TypeError, ValueError):
            return {"error": "type_id(s) or guids required"}
        for node in tree.walk():
            o = adapter._by_guid.get(node.guid)
            if o is None:
                continue
            if _object_kind_ids(o) & wanted:
                objs.append(o)
    else:
        return {"error": "type_id(s) or guids required"}

    try:
        for o in doc.selected_objects():
            o.select_set(False)
    except Exception:
        pass

    selected = 0
    for i, o in enumerate(objs):
        try:
            o.select_set(True)
            if i == 0:
                try:
                    bpy.context.view_layer.objects.active = o
                except Exception:
                    pass
            selected += 1
        except Exception:
            continue

    doc.tag_redraw()
    return {"ok": True, "selected": selected}


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------
def handle(op, payload, doc, adapter, tree, progress):
    if op == "tags_scan":
        return _scan(doc, adapter, tree, progress)
    if op == "tags_add_phong":
        return _add_phong(doc, adapter, tree, payload)
    if op == "tags_set_phong_angle":
        return _set_phong_angle(doc, adapter, tree, payload)
    if op == "tags_delete_duplicates":
        return _delete_duplicates(doc, adapter, tree, payload)
    if op == "tags_select":
        return _select(doc, adapter, tree, payload)
    return {"error": "unknown tags op: %s" % op}
