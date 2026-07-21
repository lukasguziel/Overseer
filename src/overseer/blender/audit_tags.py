"""Tags audit for Blender - there are no C4D "tags"; we audit object
attachments: modifiers, constraints, and mesh smoothing (the Phong analog).

The Blender twin of ``cinema/audit_tags.py``. Blender has no "tags", so a
"type" row is one attachment KIND: a modifier type (grouped), a constraint
type, or "Shade Smooth" (the smoothing analog of a Phong tag). Kind ids are
synthetic - a stable integer hashed from the kind string - because Blender
kinds are strings and the frontend only needs an opaque, unique selector.

Minimum target is Blender 4.2 LTS: Auto-Smooth is ONLY the "Smooth by Angle"
Geometry Nodes modifier (the old ``mesh.use_auto_smooth`` flag was removed in
4.1), so there is no legacy data path anymore.

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

from ..core.hostapi.audits import TagsAudit
from ..core.tags_logic import (
    DEFAULT_PHONG_ANGLE_DEG,
    deg_from_rad,
    dominant_angle,
)

# Name of the Geometry Nodes modifier / node group Blender's Auto-Smooth adds
# (the "Shade Auto Smooth" operator). Matched case-insensitively.
_SMOOTH_BY_ANGLE = "smooth by angle"

# Per-request cache of the resolved angle-socket identifier, keyed by node
# group name (the module is purged per request, so this never goes stale).
_ANGLE_IDENT_CACHE: dict = {}


class BlenderTagsAudit(TagsAudit):
    # -----------------------------------------------------------------------
    # small defensive readers
    # -----------------------------------------------------------------------
    def _safe_iter(self, obj, attr) -> list:
        try:
            return list(getattr(obj, attr))
        except Exception:
            return []

    def _attr(self, o, name, default):
        try:
            v = getattr(o, name)
            return v if v is not None else default
        except Exception:
            return default

    def _is_mesh(self, obj) -> bool:
        try:
            return obj.type == "MESH"
        except Exception:
            return False

    def _mesh_data(self, obj):
        try:
            data = obj.data
        except Exception:
            return None
        if data is not None and hasattr(data, "polygons"):
            return data
        return None

    def _kind_id(self, kind: str) -> int:
        """Stable synthetic int id for a kind string (opaque to the frontend)."""
        try:
            return zlib.crc32(kind.encode("utf-8")) & 0x7FFFFFFF
        except Exception:
            return 0

    def _modifier_label(self, mod) -> str:
        try:
            nm = mod.bl_rna.name
            if nm:
                return nm
        except Exception:
            pass
        return self._attr(mod, "type", "Modifier").replace("_", " ").title()

    def _constraint_label(self, con) -> str:
        base = ""
        try:
            base = con.bl_rna.name or ""
        except Exception:
            base = ""
        if not base:
            base = self._attr(con, "type", "Constraint").replace("_", " ").title()
        return base + " (constraint)"

    def _mat_key(self, mat) -> str:
        """Datablock identity: two slots pointing at the SAME material share it."""
        try:
            return mat.name_full
        except Exception:
            try:
                return "id:%d" % id(mat)
            except Exception:
                return "?"

    def _mat_name(self, mat) -> str:
        try:
            return mat.name or ""
        except Exception:
            return ""

    # -----------------------------------------------------------------------
    # mesh smoothing (the Phong analog)
    # -----------------------------------------------------------------------
    def _smooth_by_angle_modifier(self, obj):
        """The "Smooth by Angle" Geometry Nodes modifier, if present."""
        for mod in self._safe_iter(obj, "modifiers"):
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

    def _angle_socket_identifier(self, mod):
        """Identifier of the modifier's angle INPUT socket, via the node group
        interface (never blind key guesses; identifiers change across releases).
        Cached per node group name for the length of the request."""
        try:
            ng = mod.node_group
        except Exception:
            return None
        if ng is None:
            return None

        try:
            key = ng.name
        except Exception:
            key = None
        if key is not None and key in _ANGLE_IDENT_CACHE:
            return _ANGLE_IDENT_CACHE[key]

        ident = None
        named = None
        try:
            for item in ng.interface.items_tree:
                if getattr(item, "item_type", "SOCKET") != "SOCKET":
                    continue
                if getattr(item, "in_out", "") != "INPUT":
                    continue
                if getattr(item, "subtype", "") == "ANGLE":
                    ident = getattr(item, "identifier", None)
                    break
                if named is None and (getattr(item, "name", "") or "").lower() == "angle":
                    named = getattr(item, "identifier", None)
        except Exception:
            ident = None
        if ident is None:
            ident = named

        if key is not None:
            _ANGLE_IDENT_CACHE[key] = ident
        return ident

    def _read_modifier_angle(self, mod):
        """Best-effort read of the Smooth by Angle angle input (radians)."""
        ident = self._angle_socket_identifier(mod)
        if ident is None:
            return None
        try:
            v = mod[ident]
        except Exception:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        return None

    def _write_modifier_angle(self, mod, radians: float) -> bool:
        ident = self._angle_socket_identifier(mod)
        if ident is None:
            return False
        try:
            mod[ident] = radians
            return True
        except Exception:
            return False

    def _any_smooth(self, mesh) -> bool:
        """Is any polygon shade-smooth? Bulk ``foreach_get`` over ALL polygons
        (vectorised) - never decide from ``polygons[0]`` alone."""
        try:
            polys = mesh.polygons
            n = len(polys)
        except Exception:
            return False
        if not n:
            return False
        try:
            flags = [False] * n
            polys.foreach_get("use_smooth", flags)
            return any(flags)
        except Exception:
            try:
                return any(p.use_smooth for p in polys)
            except Exception:
                return False

    def _smooth_state(self, obj) -> dict:
        """(smooth, auto, angle_deg) for a mesh object.

        ``smooth`` - is it shade-smooth at all (the "has a Phong tag" analog).
        ``auto``   - does it carry Auto-Smooth (the "Smooth by Angle" modifier);
                     only these contribute an angle to the distribution.
        ``angle_deg`` - the Auto-Smooth angle in degrees, when determinable.
        """
        state = {"smooth": False, "auto": False, "angle_deg": None}
        mesh = self._mesh_data(obj)
        if mesh is None:
            return state

        if self._any_smooth(mesh):
            state["smooth"] = True

        mod = self._smooth_by_angle_modifier(obj)
        if mod is not None:
            state["auto"] = True
            state["smooth"] = True
            rad = self._read_modifier_angle(mod)
            if rad is not None:
                state["angle_deg"] = deg_from_rad(rad)

        return state

    def _shade_smooth_faces(self, obj) -> bool:
        """Set all polygon smooth flags - the "shade smooth" half of Auto-Smooth.
        Version-agnostic, needs no operator. NOT the Auto-Smooth attachment."""
        mesh = self._mesh_data(obj)
        if mesh is None:
            return False
        try:
            n = len(mesh.polygons)
            if not n:
                return False
            mesh.polygons.foreach_set("use_smooth", [True] * n)
            try:
                mesh.update()
            except Exception:
                pass
            return True
        except Exception:
            return False

    def _find_smooth_group(self, bpy):
        """An already-loaded "Smooth by Angle" node group, reusable for a direct
        modifier attach (so a batch loads the asset once, not once per object)."""
        try:
            groups = bpy.data.node_groups
        except Exception:
            return None
        try:
            for ng in groups:
                if _SMOOTH_BY_ANGLE in (getattr(ng, "name", "") or "").lower():
                    return ng
        except Exception:
            pass
        return None

    def _attach_smooth_directly(self, obj, group, radians: float, bpy) -> bool:
        """Add a Smooth-by-Angle NodesModifier reusing an existing node group -
        reliable (no operator, no asset-load race)."""
        try:
            mod = obj.modifiers.new(name="Smooth by Angle", type="NODES")
        except Exception:
            return False
        try:
            mod.node_group = group
        except Exception:
            try:
                obj.modifiers.remove(mod)
            except Exception:
                pass
            return False
        self._write_modifier_angle(mod, radians)
        try:
            obj.update_tag()
        except Exception:
            pass
        return True

    def _op_shade_auto_smooth(self, obj, radians: float, bpy):
        """Auto-Smooth via the operator - unreliable (async asset-library load
        can raise), so retry and VERIFY the modifier actually landed. Returns the
        Smooth-by-Angle modifier or None; never trusts the operator's own result."""
        for _ in range(2):
            try:
                with bpy.context.temp_override(
                        object=obj, active_object=obj,
                        selected_objects=[obj], selected_editable_objects=[obj]):
                    bpy.ops.object.shade_auto_smooth(angle=radians)
            except Exception:
                pass
            mod = self._smooth_by_angle_modifier(obj)
            if mod is not None:
                return mod
        return None

    def _attach_auto_smooth(self, obj, group, radians: float, bpy):
        """Ensure ``obj`` carries a Smooth-by-Angle modifier at ``radians``.

        Returns the node group used (so a batch can reuse it for later objects) or
        None if attachment truly failed. Reuses ``group`` via a direct modifier
        when known; otherwise falls back to the operator and adopts the group it
        loaded.
        """
        existing = self._smooth_by_angle_modifier(obj)
        if existing is not None:
            self._write_modifier_angle(existing, radians)
            return self._attr(existing, "node_group", None) or group

        if group is not None and self._attach_smooth_directly(obj, group, radians, bpy):
            return group

        mod = self._op_shade_auto_smooth(obj, radians, bpy)
        if mod is not None:
            self._write_modifier_angle(mod, radians)
            return self._attr(mod, "node_group", None) or group
        return None

    def _set_auto_smooth_angle(self, obj, radians: float, bpy) -> bool:
        """Set the Auto-Smooth angle on a mesh that already carries the modifier."""
        mod = self._smooth_by_angle_modifier(obj)
        if mod is None:
            return False
        if not self._write_modifier_angle(mod, radians):
            return False
        try:
            obj.update_tag()
        except Exception:
            pass
        return True

    # -----------------------------------------------------------------------
    # duplicate material slots
    # -----------------------------------------------------------------------
    def _duplicate_material_slots(self, obj) -> list:
        """[(material_name, count)] for materials filling more than one slot."""
        out: list = []
        seen: dict = {}
        order: list = []
        for slot in self._safe_iter(obj, "material_slots"):
            try:
                mat = slot.material
            except Exception:
                mat = None
            if mat is None:
                continue
            key = self._mat_key(mat)
            if key in seen:
                seen[key][1] += 1
            else:
                seen[key] = [self._mat_name(mat), 1]
                order.append(key)
        for key in order:
            name, count = seen[key]
            if count > 1:
                out.append((name, count))
        return out

    def _remove_duplicate_slots(self, obj, bpy) -> int:
        seen: set = set()
        dup_idx: list = []
        for i, slot in enumerate(self._safe_iter(obj, "material_slots")):
            try:
                mat = slot.material
            except Exception:
                mat = None
            if mat is None:
                continue
            key = self._mat_key(mat)
            if key in seen:
                dup_idx.append(i)
            else:
                seen.add(key)
        removed = 0
        # High index first so earlier indices stay valid as slots are removed.
        for i in sorted(dup_idx, reverse=True):
            if self._remove_slot(obj, i, bpy):
                removed += 1
        return removed

    def _remove_slot(self, obj, index: int, bpy) -> bool:
        try:
            obj.active_material_index = index
            with bpy.context.temp_override(
                    object=obj, active_object=obj,
                    selected_objects=[obj], selected_editable_objects=[obj]):
                bpy.ops.object.material_slot_remove()
            return True
        except Exception:
            pass

        # Fallback pops the mesh datablock's material by index. That index only
        # lines up with the object's slot index when EVERY slot is DATA-linked; an
        # OBJECT-linked slot (per-instance override) diverges the two arrays, so
        # refuse rather than remove the wrong material and mis-report success.
        try:
            slots = list(obj.material_slots)
        except Exception:
            return False
        if not all(self._attr(s, "link", "DATA") == "DATA" for s in slots):
            return False
        try:
            obj.data.materials.pop(index=index)
            return True
        except Exception:
            return False

    # -----------------------------------------------------------------------
    # kind ids for an object (used by tags_select on synthetic type_ids)
    # -----------------------------------------------------------------------
    def _object_kind_ids(self, obj) -> set:
        ids: set = set()
        for mod in self._safe_iter(obj, "modifiers"):
            ids.add(self._kind_id("mod:" + self._attr(mod, "type", "UNKNOWN")))
        for con in self._safe_iter(obj, "constraints"):
            ids.add(self._kind_id("con:" + self._attr(con, "type", "UNKNOWN")))
        if self._is_mesh(obj):
            state = self._smooth_state(obj)
            if state["smooth"] or state["auto"]:
                ids.add(self._kind_id("smooth"))
        return ids

    # -----------------------------------------------------------------------
    # scan
    # -----------------------------------------------------------------------
    def _add_attachment(self, types: dict, node_tags: dict, kind: str, label: str,
                        name: str) -> None:
        entry = types.get(kind)
        if entry is None:
            entry = {"type_id": self._kind_id(kind), "label": label,
                     "count": 0, "objects": []}
            types[kind] = entry
        entry["count"] += 1
        node_tags.setdefault(kind, []).append({"name": name})

    def scan(self, doc, adapter, tree, progress) -> dict:
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

            for mod in self._safe_iter(obj, "modifiers"):
                kind = "mod:" + self._attr(mod, "type", "UNKNOWN")
                self._add_attachment(types, node_tags, kind, self._modifier_label(mod),
                                     self._attr(mod, "name", ""))
                total_tags += 1

            for con in self._safe_iter(obj, "constraints"):
                kind = "con:" + self._attr(con, "type", "UNKNOWN")
                self._add_attachment(types, node_tags, kind, self._constraint_label(con),
                                     self._attr(con, "name", ""))
                total_tags += 1

            if self._is_mesh(obj):
                state = self._smooth_state(obj)
                if state["smooth"] or state["auto"]:
                    if state["auto"] and state["angle_deg"] is not None:
                        label_name = "Auto-Smooth %g°" % state["angle_deg"]
                    elif state["auto"]:
                        label_name = "Auto-Smooth"
                    else:
                        label_name = "Smooth"
                    self._add_attachment(types, node_tags, "smooth", "Shade Smooth",
                                         label_name)
                    total_tags += 1
                    if state["auto"] and state["angle_deg"] is not None:
                        deg = state["angle_deg"]
                        phong_angles[deg] = phong_angles.get(deg, 0) + 1
                else:
                    missing_phong.append({"guid": node.guid, "name": node.name})

                for mat_name, count in self._duplicate_material_slots(obj):
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
            # Blender has no Cinema-4D-style Phong tag, and professional projects
            # don't rely on the auto-smooth analog, so hide the smoothing UI (the
            # missing-phong stat, the add-phong card and the angle card). The type
            # inventory + duplicate-material-slot audit stay.
            "phong": False,
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

    def _current_phong_angles(self, adapter, tree) -> dict:
        counts: dict = {}
        for node in tree.walk():
            obj = adapter._by_guid.get(node.guid)
            if obj is None or not self._is_mesh(obj):
                continue
            state = self._smooth_state(obj)
            if state["auto"] and state["angle_deg"] is not None:
                deg = state["angle_deg"]
                counts[deg] = counts.get(deg, 0) + 1
        return counts

    # -----------------------------------------------------------------------
    # mutations
    # -----------------------------------------------------------------------
    def add_phong(self, doc, adapter, tree, payload) -> dict:
        bpy = adapter.bpy
        guids = payload.get("guids")
        wanted = set(guids) if guids is not None else None
        angle_deg = dominant_angle(self._current_phong_angles(adapter, tree))
        if angle_deg is None:
            angle_deg = DEFAULT_PHONG_ANGLE_DEG
        radians = math.radians(float(angle_deg))

        targets: list = []
        for node in tree.walk():
            if wanted is not None and node.guid not in wanted:
                continue
            obj = adapter._by_guid.get(node.guid)
            if obj is None or not self._is_mesh(obj):
                continue
            state = self._smooth_state(obj)
            if state["smooth"] or state["auto"]:
                continue
            targets.append((node, obj))

        group = self._find_smooth_group(bpy)
        applied = 0
        for _node, obj in targets:
            self._shade_smooth_faces(obj)
            used = self._attach_auto_smooth(obj, group, radians, bpy)
            if used is not None:
                group = used
                applied += 1

        if applied:
            doc.undo_push("Overseer: add auto-smooth")
        doc.tag_redraw()
        return {"ok": True, "applied": applied,
                "angle_deg": round(float(angle_deg), 1)}

    def set_phong_angle(self, doc, adapter, tree, payload) -> dict:
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
            if obj is None or not self._is_mesh(obj):
                continue
            if not self._smooth_state(obj)["auto"]:
                continue
            if self._set_auto_smooth_angle(obj, radians, bpy):
                applied += 1

        if applied:
            doc.undo_push("Overseer: set auto-smooth angle")
        doc.tag_redraw()
        return {"ok": True, "applied": applied, "angle_deg": round(angle_deg, 1)}

    def delete_duplicates(self, doc, adapter, tree, payload) -> dict:
        bpy = adapter.bpy
        guids = payload.get("guids")
        wanted = set(guids) if guids is not None else None

        deleted = 0
        for node in tree.walk():
            if wanted is not None and node.guid not in wanted:
                continue
            obj = adapter._by_guid.get(node.guid)
            if obj is None or not self._is_mesh(obj):
                continue
            deleted += self._remove_duplicate_slots(obj, bpy)

        if deleted:
            doc.undo_push("Overseer: remove duplicate material slots")
        doc.tag_redraw()
        return {"ok": True, "deleted": deleted}

    def select(self, doc, adapter, tree, payload) -> dict:
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
                if self._object_kind_ids(o) & wanted:
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


AUDIT = BlenderTagsAudit()
