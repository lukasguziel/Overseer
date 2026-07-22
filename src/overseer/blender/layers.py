from __future__ import annotations

from ..core.defaults import LAYER_COLORS
from ..core.layers.base import LayersBase

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


class BlenderLayers(LayersBase):

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

    def _scene_collection_names(self) -> set:
        names: set = set()
        for col in self._scene_collections():
            try:
                nm = col.name
            except Exception:
                nm = None
            if nm:
                names.add(nm)
        return names

    def _scene_layer_name(self, obj, scene_names: set, master) -> str | None:
        try:
            cols = obj.users_collection
        except Exception:
            return None
        for c in cols:
            try:
                if master is not None and c == master:
                    continue
                name = c.name
                if name and name in scene_names:
                    return name
            except Exception:
                continue
        return None

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

    def get_layer_handles(self) -> list:
        return self._scene_collections()

    def get_layer_name(self, handle) -> str | None:
        try:
            return handle.name
        except Exception:
            return None

    def get_layer_meta(self, handle) -> dict:
        meta: dict = {"color": self._color_from_tag(handle)}
        try:
            meta["view"] = not bool(handle.hide_viewport)
        except Exception:
            pass
        try:
            meta["render"] = not bool(handle.hide_render)
        except Exception:
            pass
        return meta

    def _layer_object_counts(self) -> dict:
        counts: dict = {}
        master = self._master_collection()
        scene_names = self._scene_collection_names()
        for obj in self.doc.objects():
            try:
                nm = self._scene_layer_name(obj, scene_names, master)
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

    def _reference_names(self) -> set:
        names: set = set()
        try:
            objs = list(self.bpy.data.objects)
        except Exception:
            objs = []
        for obj in objs:
            try:
                if getattr(obj, "instance_type", None) == "COLLECTION":
                    ic = getattr(obj, "instance_collection", None)
                    nm = getattr(ic, "name", None)
                    if nm:
                        names.add(nm)
            except Exception:
                pass
            try:
                for ps in getattr(obj, "particle_systems", None) or []:
                    st = getattr(ps, "settings", None)
                    ic = getattr(st, "instance_collection", None)
                    nm = getattr(ic, "name", None)
                    if nm:
                        names.add(nm)
            except Exception:
                pass
        return names

    def _link_count(self, col) -> int:
        try:
            name = col.name
        except Exception:
            return 0
        if not name:
            return 0
        count = 0
        try:
            for c in self.bpy.data.collections:
                try:
                    for ch in c.children:
                        if ch.name == name:
                            count += 1
                except Exception:
                    continue
        except Exception:
            pass
        master = self._master_collection()
        if master is not None:
            try:
                for ch in master.children:
                    if ch.name == name:
                        count += 1
            except Exception:
                pass
        return count

    def _extra_referenced(self, col) -> bool:
        users = getattr(col, "users", None)
        if not isinstance(users, int):
            return False
        return users > self._link_count(col)

    def _is_branch_empty(self, col, keep: set, ref_names: set) -> bool:
        try:
            name = col.name
        except Exception:
            return False
        if name in keep:
            return False
        if name in ref_names:
            return False
        if self._collection_object_count(col) > 0:
            return False
        if self._extra_referenced(col):
            return False
        try:
            children = list(col.children)
        except Exception:
            children = []
        for c in children:
            if not self._is_branch_empty(c, keep, ref_names):
                return False
        return True

    def _remove_collection(self, col, seen: set | None = None) -> int:
        seen = seen if seen is not None else set()
        key = id(col)
        if key in seen:
            return 0
        seen.add(key)
        removed = 0
        try:
            children = list(col.children)
        except Exception:
            children = []
        for c in children:
            removed += self._remove_collection(c, seen)
        try:
            self.bpy.data.collections.remove(col)
            removed += 1
        except Exception:
            pass
        return removed

    def delete_layer(self, name: str) -> int:
        ref_names = self._reference_names()
        target = None
        for col in self._scene_collections():
            try:
                if col.name == name and self._is_branch_empty(
                        col, set(), ref_names):
                    target = col
                    break
            except Exception:
                continue
        if target is None:
            return 0
        removed = self._remove_collection(target)
        if not removed:
            return 0
        self.doc.undo_push("Delete layer")
        self.doc.tag_redraw()
        return 1

    def delete_empty_layers(self, keep: set | None = None) -> int:
        keep = keep or set()
        master = self._master_collection()
        if master is None:
            return 0
        ref_names = self._reference_names()
        try:
            top = list(master.children)
        except Exception:
            top = []
        targets = [c for c in top if self._is_branch_empty(c, keep, ref_names)]
        if not targets:
            return 0
        seen: set = set()
        removed = 0
        for col in targets:
            try:
                if self._remove_collection(col, seen) > 0:
                    removed += 1
            except Exception:
                continue
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
            try:
                col.color_tag = self._nearest_color_tag(rgb)
                changed += 1
            except Exception:
                continue
        if changed:
            self.doc.undo_push("Set layer colors")
            self.doc.tag_redraw()
        return changed

    def _collection_cache(self) -> dict:
        cache = getattr(self, "_col_cache", None)
        if cache is None:
            cache = {}
            self._col_cache = cache
        return cache

    def _link_under_master(self, col) -> None:
        master = self._master_collection()
        if master is None:
            return
        try:
            name = col.name
        except Exception:
            name = None
        try:
            already = any(getattr(ch, "name", None) == name
                          for ch in master.children)
        except Exception:
            already = False
        if already:
            return
        try:
            master.children.link(col)
        except Exception:
            pass

    def _find_or_create_collection(self, name: str):
        cache = self._collection_cache()
        cached = cache.get(name)
        if cached is not None:
            return cached

        for col in self._scene_collections():
            try:
                if col.name == name:
                    cache[name] = col
                    return col
            except Exception:
                continue

        existing = None
        try:
            existing = self.bpy.data.collections.get(name)
        except Exception:
            existing = None
        if existing is not None:
            self._link_under_master(existing)
            cache[name] = existing
            try:
                cache[existing.name] = existing
            except Exception:
                pass
            return existing

        try:
            col = self.bpy.data.collections.new(name)
        except Exception:
            return None
        self._link_under_master(col)
        rgb = LAYER_COLORS.get(name)
        if rgb is not None:
            try:
                col.color_tag = self._nearest_color_tag(rgb)
            except Exception:
                pass
        cache[name] = col
        try:
            cache[col.name] = col
        except Exception:
            pass
        return col

    def _current_layer_name(self, obj) -> str:
        master = self._master_collection()
        scene_names = self._scene_collection_names()
        try:
            nm = self._scene_layer_name(obj, scene_names, master)
        except Exception:
            nm = None
        return nm or ""
