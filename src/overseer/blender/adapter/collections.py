from __future__ import annotations

from ...core.defaults import LAYER_COLORS
from .readers import layer_name

COLOR_TAG_RGB = {
    "COLOR_01": (0.94, 0.25, 0.25),
    "COLOR_02": (0.94, 0.51, 0.17),
    "COLOR_03": (0.93, 0.83, 0.33),
    "COLOR_04": (0.37, 0.75, 0.26),
    "COLOR_05": (0.26, 0.57, 0.92),
    "COLOR_06": (0.62, 0.36, 0.85),
    "COLOR_07": (0.93, 0.47, 0.78),
    "COLOR_08": (0.60, 0.42, 0.31),
}


class CollectionOps:

    def _scene_collections(self) -> list:
        master = self._master_collection()
        out: list = []
        seen: set = set()

        def visit(col):
            try:
                children = list(col.children)
            except Exception:
                children = []
            for c in children:
                key = id(c)
                if key in seen:
                    continue
                seen.add(key)
                out.append(c)
                visit(c)

        if master is not None:
            visit(master)
        return out

    @staticmethod
    def _nearest_color_tag(rgb) -> str:
        try:
            r, g, b = float(rgb[0]), float(rgb[1]), float(rgb[2])
        except Exception:
            return "NONE"
        best = "NONE"
        best_d = None
        for tag, (tr, tg, tb) in COLOR_TAG_RGB.items():
            d = (r - tr) ** 2 + (g - tg) ** 2 + (b - tb) ** 2
            if best_d is None or d < best_d:
                best_d = d
                best = tag
        return best

    def _color_from_tag(self, col) -> list | None:
        try:
            tag = col.color_tag
        except Exception:
            return None
        if not tag or tag == "NONE":
            return None
        rgb = COLOR_TAG_RGB.get(tag)
        if rgb is None:
            return None
        return [round(rgb[0], 3), round(rgb[1], 3), round(rgb[2], 3)]

    def scan_layers(self) -> list:
        out: list = []
        for col in self._scene_collections():
            try:
                name = col.name
            except Exception:
                continue
            entry = {"name": name, "color": None,
                     "solo": False, "view": True, "render": True,
                     "locked": False, "materials": 0, "tags": 0}
            entry["color"] = self._color_from_tag(col)
            try:
                entry["view"] = not bool(col.hide_viewport)
            except Exception:
                pass
            try:
                entry["render"] = not bool(col.hide_render)
            except Exception:
                pass
            out.append(entry)
        return out

    def _layer_object_counts(self) -> dict:
        counts: dict = {}
        master = self._master_collection()
        for obj in self.doc.objects():
            try:
                nm = layer_name(obj, master)
            except Exception:
                nm = None
            if nm:
                counts[nm] = counts.get(nm, 0) + 1
        return counts

    def _collection_object_count(self, col) -> int:
        try:
            return len(col.objects)
        except Exception:
            return 0

    def _is_branch_empty(self, col, keep: set) -> bool:
        try:
            name = col.name
        except Exception:
            return False
        if name in keep:
            return False
        if self._collection_object_count(col) > 0:
            return False
        try:
            children = list(col.children)
        except Exception:
            children = []
        for c in children:
            if not self._is_branch_empty(c, keep):
                return False
        return True

    def _remove_collection(self, col) -> bool:
        try:
            children = list(col.children)
        except Exception:
            children = []
        for c in children:
            self._remove_collection(c)
        try:
            self.bpy.data.collections.remove(col)
            return True
        except Exception:
            return False

    def delete_layer(self, name: str) -> int:
        target = None
        for col in self._scene_collections():
            try:
                if col.name == name and self._is_branch_empty(col, set()):
                    target = col
                    break
            except Exception:
                continue
        if target is None:
            return 0
        if not self._remove_collection(target):
            return 0
        self.doc.undo_push("Delete layer")
        self.doc.tag_redraw()
        return 1

    def delete_empty_layers(self, keep: set | None = None) -> int:
        keep = keep or set()
        master = self._master_collection()
        if master is None:
            return 0
        try:
            top = list(master.children)
        except Exception:
            top = []
        targets = [c for c in top if self._is_branch_empty(c, keep)]
        if not targets:
            return 0
        removed = 0
        for col in targets:
            if self._remove_collection(col):
                removed += 1
        if removed:
            self.doc.undo_push("Delete empty layers")
            self.doc.tag_redraw()
        return removed

    def set_layer_colors(self, colors: dict) -> int:
        if not colors:
            return 0
        targets: list = []
        for col in self._scene_collections():
            try:
                rgb = colors.get(col.name)
            except Exception:
                rgb = None
            if rgb is not None:
                targets.append((col, rgb))
        if not targets:
            return 0
        changed = 0
        for col, rgb in targets:
            tag = self._nearest_color_tag(rgb)
            try:
                col.color_tag = tag
                changed += 1
            except Exception:
                continue
        if changed:
            self.doc.undo_push("Set layer colors")
            self.doc.tag_redraw()
        return changed

    def _find_or_create_collection(self, name: str):
        for col in self._scene_collections():
            try:
                if col.name == name:
                    return col
            except Exception:
                continue
        try:
            col = self.bpy.data.collections.new(name)
        except Exception:
            return None
        master = self._master_collection()
        if master is not None:
            try:
                master.children.link(col)
            except Exception:
                pass
        rgb = LAYER_COLORS.get(name)
        if rgb is not None:
            try:
                col.color_tag = self._nearest_color_tag(rgb)
            except Exception:
                pass
        return col

    def _current_layer_name(self, obj) -> str:
        master = self._master_collection()
        try:
            nm = layer_name(obj, master)
        except Exception:
            nm = None
        return nm or ""
