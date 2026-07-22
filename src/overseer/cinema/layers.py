from __future__ import annotations

import c4d

from ..core.defaults import LAYER_COLORS
from ..core.layers.base import LayersBase
from ..core.layers.report import layer_entry
from .scene.readers import layer_name


class CinemaLayers(LayersBase):

    @staticmethod
    def _linked_layer_name(node) -> str | None:
        try:
            lay = node[c4d.ID_LAYER_LINK]
            return lay.GetName() if lay is not None else None
        except Exception:
            return None

    def _layer_ref_counts(self) -> tuple[dict, dict]:
        mats: dict = {}
        tags: dict = {}
        try:
            for m in self.doc.GetMaterials():
                nm = self._linked_layer_name(m)
                if nm:
                    mats[nm] = mats.get(nm, 0) + 1
        except Exception:
            pass

        def visit(op):
            while op:
                try:
                    for tag in op.GetTags():
                        nm = self._linked_layer_name(tag)
                        if nm:
                            tags[nm] = tags.get(nm, 0) + 1
                except Exception:
                    pass
                visit(op.GetDown())
                op = op.GetNext()

        visit(self.doc.GetFirstObject())
        return mats, tags

    def _layer_object_counts(self) -> dict:
        counts: dict = {}

        def visit(op):
            while op:
                nm = layer_name(op)
                if nm:
                    counts[nm] = counts.get(nm, 0) + 1
                visit(op.GetDown())
                op = op.GetNext()

        visit(self.doc.GetFirstObject())
        return counts

    def scan_layers(self) -> list[dict]:
        out: list[dict] = []
        try:
            root = self.doc.GetLayerObjectRoot()
        except Exception:
            return out
        mats, tags = self._layer_ref_counts()
        lay = root.GetDown() if root is not None else None
        while lay:
            name = lay.GetName()
            entry = layer_entry(name, materials=mats.get(name, 0),
                                tags=tags.get(name, 0))
            try:
                d = lay.GetLayerData(self.doc) or {}
                col = d.get("color")
                if col is not None:
                    entry["color"] = [round(col.x, 3), round(col.y, 3),
                                      round(col.z, 3)]
                entry["solo"] = bool(d.get("solo", False))
                entry["view"] = bool(d.get("view", True))
                entry["render"] = bool(d.get("render", True))
                entry["locked"] = bool(d.get("locked", False))
            except Exception:
                pass
            out.append(entry)
            lay = lay.GetNext()
        return out

    def _is_layer_empty(self, name: str, obj_counts: dict,
                        mats: dict, tags: dict) -> bool:
        return (obj_counts.get(name, 0) == 0 and mats.get(name, 0) == 0
                and tags.get(name, 0) == 0)

    def _is_layer_branch_empty(self, lay, keep: set, obj_counts: dict,
                               mats: dict, tags: dict) -> bool:
        name = lay.GetName()
        if name in keep:
            return False
        if not self._is_layer_empty(name, obj_counts, mats, tags):
            return False
        child = lay.GetDown()
        while child:
            if not self._is_layer_branch_empty(child, keep, obj_counts,
                                               mats, tags):
                return False
            child = child.GetNext()
        return True

    def delete_empty_layers(self, keep: set | None = None) -> int:
        keep = keep or set()
        try:
            root = self.doc.GetLayerObjectRoot()
        except Exception:
            root = None
        if root is None:
            return 0
        obj_counts = self._layer_object_counts()
        mats, tags = self._layer_ref_counts()
        targets: list = []
        lay = root.GetDown()
        while lay:
            nxt = lay.GetNext()
            if self._is_layer_branch_empty(lay, keep, obj_counts, mats, tags):
                targets.append(lay)
            lay = nxt
        if not targets:
            return 0

        self.doc.StartUndo()
        for lay in targets:
            self.doc.AddUndo(c4d.UNDOTYPE_DELETE, lay)
            lay.Remove()
        self.doc.EndUndo()
        c4d.EventAdd()
        return len(targets)

    def delete_layer(self, name: str) -> int:
        try:
            root = self.doc.GetLayerObjectRoot()
        except Exception:
            root = None
        if root is None:
            return 0
        obj_counts = self._layer_object_counts()
        mats, tags = self._layer_ref_counts()
        target = None
        lay = root.GetDown()
        while lay:
            if lay.GetName() == name and self._is_layer_branch_empty(
                    lay, set(), obj_counts, mats, tags):
                target = lay
                break
            lay = lay.GetNext()
        if target is None:
            return 0

        self.doc.StartUndo()
        self.doc.AddUndo(c4d.UNDOTYPE_DELETE, target)
        target.Remove()
        self.doc.EndUndo()
        c4d.EventAdd()
        return 1

    def set_layer_colors(self, colors: dict) -> int:
        try:
            root = self.doc.GetLayerObjectRoot()
        except Exception:
            root = None
        if root is None or not colors:
            return 0
        targets: list = []
        lay = root.GetDown()
        while lay:
            col = colors.get(lay.GetName())
            if col is not None:
                targets.append((lay, col))
            lay = lay.GetNext()
        if not targets:
            return 0

        self.doc.StartUndo()
        for lay, col in targets:
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, lay)
            data = lay.GetLayerData(self.doc) or {}
            data["color"] = c4d.Vector(float(col[0]), float(col[1]),
                                       float(col[2]))
            lay.SetLayerData(self.doc, data)
        self.doc.EndUndo()
        c4d.EventAdd()
        return len(targets)

    def _find_or_create_layer(self, name: str, created: list, cache: dict):
        if name in cache:
            return cache[name]
        root = self.doc.GetLayerObjectRoot()
        lay = root.GetDown()
        while lay:
            if lay.GetName() == name:
                cache[name] = lay
                return lay
            lay = lay.GetNext()
        layer = c4d.documents.LayerObject()
        layer.SetName(name)
        col = LAYER_COLORS.get(name)
        if col is not None:
            try:
                layer[c4d.ID_LAYER_COLOR] = c4d.Vector(*col)
            except Exception:
                pass
        layer.InsertUnder(root)
        self.doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, layer)
        created.append(layer)
        cache[name] = layer
        return layer

    def _current_layer_name(self, obj) -> str:
        try:
            lay = obj.GetLayerObject(self.doc)
            return lay.GetName() if lay is not None else ""
        except Exception:
            return ""
