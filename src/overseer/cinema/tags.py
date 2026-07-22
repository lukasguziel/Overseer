from __future__ import annotations

import c4d

from ..core.tags.audit import TagsAudit
from ..core.tags.logic import (
    DEFAULT_PHONG_ANGLE_DEG,
    deg_from_rad,
    dominant_angle,
    merge_selection_types,
)

_TPHONG = getattr(c4d, "Tphong", 5612)
_TTEXTURE = getattr(c4d, "Ttexture", 5616)
_TEXTURETAG_MATERIAL = getattr(c4d, "TEXTURETAG_MATERIAL", 1000)
_PHONGTAG_PHONG_ANGLE = getattr(c4d, "PHONGTAG_PHONG_ANGLE", 5501)
_PHONGTAG_PHONG_ANGLELIMIT = getattr(c4d, "PHONGTAG_PHONG_ANGLELIMIT", 5500)
_PHONGTAG_PHONG_USEEDGES = getattr(c4d, "PHONGTAG_PHONG_USEEDGES", 5503)

_UNDO_NEW = getattr(c4d, "UNDOTYPE_NEWTAG", getattr(c4d, "UNDOTYPE_NEW", 2))
_UNDO_CHANGE = getattr(c4d, "UNDOTYPE_CHANGE", 0)
_UNDO_DELETE = getattr(c4d, "UNDOTYPE_DELETE", 4)


_INTERNAL_TAG_TYPES = {
    tid for tid in (
        getattr(c4d, "Tpoint", 5600),
        getattr(c4d, "Tpolygon", 5604),
        getattr(c4d, "Ttangent", 5617),
        getattr(c4d, "Tsegment", 5672),
        getattr(c4d, "Tline", None),
        getattr(c4d, "Tsds", None),
        getattr(c4d, "Tsdsdata", None),
        getattr(c4d, "Tbaselist4d", None),
    ) if tid is not None
}

_SELECTION_KINDS = {
    getattr(c4d, "Tpointselection", 5674): "point",
    getattr(c4d, "Tpolygonselection", 5673): "polygon",
    getattr(c4d, "Tedgeselection", 5701): "edge",
}

_TAG_VISIBLE = getattr(c4d, "TAG_VISIBLE", 4)


class CinemaTagsAudit(TagsAudit):
    def _type_visible(self, type_id: int, cache: dict) -> bool:
        cached = cache.get(type_id)
        if cached is None:
            try:
                plug = c4d.plugins.FindPlugin(type_id, c4d.PLUGINTYPE_TAG)
                cached = plug is None or bool(plug.GetInfo() & _TAG_VISIBLE)
            except Exception:
                cached = True
            cache[type_id] = cached
        return cached

    def _tag_type_label(self, tag) -> str:
        try:
            name = tag.GetTypeName()
            if name:
                return name
        except Exception:
            pass
        try:
            name = c4d.GetObjectName(tag.GetType())
            if name and name.strip():
                return name
        except Exception:
            pass
        try:
            return "Tag %d" % tag.GetType()
        except Exception:
            return "Tag (unknown)"

    def _has_phong(self, obj) -> bool:
        try:
            return obj.GetTag(_TPHONG) is not None
        except Exception:
            return False

    def scan(self, doc, adapter, tree, progress) -> dict:
        nodes = list(tree.walk())
        total = len(nodes)

        types: dict = {}
        missing_phong: list = []
        duplicate_material_tags: list = []
        phong_angles: dict = {}
        visible_cache: dict = {}
        total_tags = 0

        for i, node in enumerate(nodes):
            if progress and i % 50 == 0:
                progress("Scanning tags", i, total, node.name)
            obj = adapter._by_guid.get(node.guid)
            if obj is None:
                continue
            try:
                tags = obj.GetTags() or []
            except Exception:
                tags = []

            seen_materials: dict = {}
            node_tags: dict = {}
            for tag in tags:
                try:
                    type_id = tag.GetType()
                    if (type_id in _INTERNAL_TAG_TYPES
                            or not self._type_visible(type_id, visible_cache)):
                        continue
                    total_tags += 1
                    entry = types.get(type_id)
                    if entry is None:
                        entry = {"type_id": type_id, "label": self._tag_type_label(tag),
                                 "count": 0, "objects": []}
                        types[type_id] = entry
                    entry["count"] += 1
                    try:
                        tag_name = tag.GetName()
                    except Exception:
                        tag_name = ""
                    node_tags.setdefault(type_id, []).append({"name": tag_name})

                    if type_id == _TTEXTURE:
                        try:
                            mat = tag[_TEXTURETAG_MATERIAL]
                        except Exception:
                            mat = None
                        if mat is not None:
                            try:
                                mat_name = mat.GetName()
                            except Exception:
                                mat_name = ""
                            key = id(mat)
                            seen_materials[key] = (
                                seen_materials.get(key, (mat_name, 0))[0],
                                seen_materials.get(key, (mat_name, 0))[1] + 1)

                    if type_id == _TPHONG:
                        try:
                            rad = tag[_PHONGTAG_PHONG_ANGLE]
                        except Exception:
                            rad = None
                        if rad is not None:
                            deg = deg_from_rad(float(rad))
                            phong_angles[deg] = phong_angles.get(deg, 0) + 1
                except Exception:
                    continue

            for type_id, tag_refs in node_tags.items():
                types[type_id]["objects"].append(
                    {"guid": node.guid, "name": node.name, "tags": tag_refs})

            for _key, (mat_name, count) in seen_materials.items():
                if count > 1:
                    duplicate_material_tags.append(
                        {"guid": node.guid, "name": node.name,
                         "material": mat_name, "count": count})

            if node.category == "mesh" and not self._has_phong(obj):
                missing_phong.append({"guid": node.guid, "name": node.name})

        if progress:
            progress("Scanning tags", total, total, "")

        type_list = sorted(types.values(), key=lambda e: (-e["count"], e["label"]))
        type_list = merge_selection_types(type_list, _SELECTION_KINDS)
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

    def add_phong(self, doc, adapter, tree, payload) -> dict:
        guids = payload.get("guids")
        wanted = set(guids) if guids is not None else None
        angle_deg = dominant_angle(self._current_phong_angles(adapter, tree))
        if angle_deg is None:
            angle_deg = DEFAULT_PHONG_ANGLE_DEG
        rad = c4d.utils.DegToRad(float(angle_deg))

        applied = 0
        doc.StartUndo()
        for node in tree.walk():
            if wanted is not None and node.guid not in wanted:
                continue
            obj = adapter._by_guid.get(node.guid)
            if obj is None or node.category != "mesh" or self._has_phong(obj):
                continue
            try:
                tag = c4d.BaseTag(_TPHONG)
                if tag is None:
                    continue
                obj.InsertTag(tag)
                try:
                    tag[_PHONGTAG_PHONG_ANGLE] = rad
                    tag[_PHONGTAG_PHONG_ANGLELIMIT] = True
                except Exception:
                    pass
                doc.AddUndo(_UNDO_NEW, tag)
                applied += 1
            except Exception:
                continue
        doc.EndUndo()
        c4d.EventAdd()
        return {"ok": True, "applied": applied, "angle_deg": round(float(angle_deg), 1)}

    def _current_phong_angles(self, adapter, tree) -> dict:
        counts: dict = {}
        for node in tree.walk():
            obj = adapter._by_guid.get(node.guid)
            if obj is None:
                continue
            try:
                tag = obj.GetTag(_TPHONG)
            except Exception:
                tag = None
            if tag is None:
                continue
            try:
                rad = tag[_PHONGTAG_PHONG_ANGLE]
            except Exception:
                rad = None
            if rad is not None:
                deg = deg_from_rad(float(rad))
                counts[deg] = counts.get(deg, 0) + 1
        return counts

    def set_phong_angle(self, doc, adapter, tree, payload) -> dict:
        try:
            angle_deg = float(payload.get("angle_deg"))
        except (TypeError, ValueError):
            return {"error": "angle_deg must be a number"}
        rad = c4d.utils.DegToRad(angle_deg)
        guids = payload.get("guids")
        wanted = set(guids) if guids is not None else None

        applied = 0
        doc.StartUndo()
        for node in tree.walk():
            if wanted is not None and node.guid not in wanted:
                continue
            obj = adapter._by_guid.get(node.guid)
            if obj is None:
                continue
            try:
                tag = obj.GetTag(_TPHONG)
            except Exception:
                tag = None
            if tag is None:
                continue
            try:
                doc.AddUndo(_UNDO_CHANGE, tag)
                tag[_PHONGTAG_PHONG_ANGLE] = rad
                applied += 1
            except Exception:
                continue
        doc.EndUndo()
        c4d.EventAdd()
        return {"ok": True, "applied": applied, "angle_deg": round(angle_deg, 1)}

    def delete_duplicates(self, doc, adapter, tree, payload) -> dict:
        guids = payload.get("guids")
        wanted = set(guids) if guids is not None else None

        deleted = 0
        doc.StartUndo()
        for node in tree.walk():
            if wanted is not None and node.guid not in wanted:
                continue
            obj = adapter._by_guid.get(node.guid)
            if obj is None:
                continue
            try:
                tags = obj.GetTags() or []
            except Exception:
                continue
            seen: set = set()
            for tag in tags:
                try:
                    if tag.GetType() != _TTEXTURE:
                        continue
                    mat = tag[_TEXTURETAG_MATERIAL]
                except Exception:
                    continue
                if mat is None:
                    continue
                key = id(mat)
                if key in seen:
                    try:
                        doc.AddUndo(_UNDO_DELETE, tag)
                        tag.Remove()
                        deleted += 1
                    except Exception:
                        continue
                else:
                    seen.add(key)
        doc.EndUndo()
        c4d.EventAdd()
        return {"ok": True, "deleted": deleted}

    def select(self, doc, adapter, tree, payload) -> dict:
        guids = payload.get("guids")
        type_ids = payload.get("type_ids") or [payload.get("type_id")]

        if guids is not None:
            wanted = set(guids)
            objs = [adapter._by_guid.get(g) for g in wanted]
        else:
            try:
                type_ids = [int(t) for t in type_ids]
            except (TypeError, ValueError):
                return {"error": "type_id(s) or guids required"}
            objs = []
            for node in tree.walk():
                obj = adapter._by_guid.get(node.guid)
                if obj is None:
                    continue
                try:
                    if any(obj.GetTag(t) is not None for t in type_ids):
                        objs.append(obj)
                except Exception:
                    continue

        objs = [o for o in objs if o is not None]
        selected = 0
        for i, obj in enumerate(objs):
            try:
                mode = c4d.SELECTION_NEW if i == 0 else c4d.SELECTION_ADD
                doc.SetActiveObject(obj, mode)
                selected += 1
            except Exception:
                continue
        c4d.EventAdd()
        return {"ok": True, "selected": selected}


AUDIT = CinemaTagsAudit()
