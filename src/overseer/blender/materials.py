from __future__ import annotations

import os

from ..core.materials import logic as mat_logic
from ..core.materials.logic import is_internal_material
from .constants import INTERNAL_MATERIAL_PREFIXES
from .scene.readers import editor_hidden


class MaterialOps:

    def _is_internal_material(self, name: str) -> bool:
        n = name or ""
        if is_internal_material(n):
            return True
        try:
            return n.startswith(INTERNAL_MATERIAL_PREFIXES)
        except Exception:
            return False

    def _all_objects(self) -> list:
        try:
            return list(self.bpy.data.objects)
        except Exception:
            try:
                return self.doc.objects()
            except Exception:
                return []

    def _fake_user_names(self) -> set:
        out: set = set()
        try:
            for m in self.bpy.data.materials:
                try:
                    if getattr(m, "use_fake_user", False):
                        out.add(m.name_full)
                except Exception:
                    continue
        except Exception:
            return out
        return out

    def _scene_material_usage(self) -> tuple:
        used_any: set = set()
        used_visible: set = set()
        for obj in self._all_objects():
            try:
                visible = not editor_hidden(obj)
            except Exception:
                visible = False
            try:
                slots = obj.material_slots
            except Exception:
                continue
            for slot in slots:
                try:
                    mat = slot.material
                    key = mat.name_full if mat is not None else None
                except Exception:
                    key = None
                if key is None:
                    continue
                used_any.add(key)
                if visible:
                    used_visible.add(key)

        keep = self._fake_user_names()
        used_any |= keep
        used_visible |= keep
        return used_any, used_visible

    def _material_images(self, mat) -> list:
        out: list = []
        try:
            if not getattr(mat, "use_nodes", False):
                return out
            tree = mat.node_tree
            if tree is None:
                return out
            self._collect_tree_images(tree, out, set())
        except Exception:
            return out
        return out

    def _collect_tree_images(self, tree, out: list, seen: set) -> None:
        try:
            tid = id(tree)
        except Exception:
            tid = None
        if tid is not None:
            if tid in seen:
                return
            seen.add(tid)
        try:
            nodes = tree.nodes
        except Exception:
            return
        for node in nodes:
            try:
                img = getattr(node, "image", None)
                if img is not None:
                    out.append(img)
            except Exception:
                pass
            try:
                if getattr(node, "type", None) == "GROUP":
                    sub = getattr(node, "node_tree", None)
                    if sub is not None:
                        self._collect_tree_images(sub, out, seen)
            except Exception:
                continue

    def _image_abspath(self, img, raw: str) -> str:
        try:
            lib = getattr(img, "library", None)
            return self.bpy.path.abspath(raw, library=lib)
        except Exception:
            try:
                return self.bpy.path.abspath(raw)
            except Exception:
                return raw

    def _missing_image(self, img, mat_name: str):
        try:
            if getattr(img, "packed_file", None) is not None:
                return None
        except Exception:
            pass
        try:
            raw = img.filepath_raw or img.filepath or ""
        except Exception:
            raw = ""
        if not raw:
            return None
        try:
            if img.source in ("GENERATED", "VIEWER"):
                return None
        except Exception:
            pass
        try:
            tiled = img.source == "TILED"
        except Exception:
            tiled = False
        if tiled:
            return self._missing_tiled(img, mat_name, raw)

        resolved = self._image_abspath(img, raw)
        if resolved and os.path.isfile(resolved):
            return None
        return {"material": mat_name, "file": os.path.basename(str(raw))}

    def _missing_tiled(self, img, mat_name: str, raw: str):
        has_token = "<UDIM>" in raw or "<UVTILE>" in raw
        if not has_token:
            return None
        try:
            tiles = list(img.tiles)
        except Exception:
            tiles = []
        if not tiles:
            return None
        for tile in tiles:
            try:
                num = int(tile.number)
            except Exception:
                continue
            candidate = raw
            if "<UDIM>" in candidate:
                candidate = candidate.replace("<UDIM>", str(num))
            if "<UVTILE>" in candidate:
                u = (num - 1001) % 10 + 1
                v = (num - 1001) // 10 + 1
                candidate = candidate.replace("<UVTILE>", "u%d_v%d" % (u, v))
            resolved = self._image_abspath(img, candidate)
            if resolved and os.path.isfile(resolved):
                return None
        return {"material": mat_name, "file": os.path.basename(str(raw))}

    def scan_materials(self, include_hidden: bool = True,
                       accepted=None) -> dict:
        accepted = set(accepted or ())
        try:
            mats = list(self.bpy.data.materials)
        except Exception:
            return mat_logic.scan_result(0, [], [], [], accepted, [])

        used_any, used_visible = self._scene_material_usage()

        unused: list = []
        only_hidden: list = []
        accepted_out: list = []
        missing: list = []
        seen_images: set = set()
        for m in mats:
            try:
                name = m.name_full
            except Exception:
                continue
            if self._is_internal_material(name):
                continue

            nowhere = name not in used_any
            hidden_only = (not nowhere) and name not in used_visible
            if nowhere or (hidden_only and include_hidden):
                if name in accepted:
                    accepted_out.append(name)
                else:
                    unused.append(name)
                    if hidden_only:
                        only_hidden.append(name)

            for img in self._material_images(m):
                try:
                    ident = img.name_full
                except Exception:
                    ident = id(img)
                if (name, ident) in seen_images:
                    continue
                seen_images.add((name, ident))
                info = self._missing_image(img, name)
                if info is not None:
                    missing.append(info)

        return mat_logic.scan_result(len(mats), unused, only_hidden,
                                      accepted_out, accepted, missing)

    def focus_material(self, name: str) -> dict:
        target = None
        try:
            for m in self.bpy.data.materials:
                if m.name_full == name:
                    target = m
                    break
        except Exception:
            target = None
        if target is None:
            return {"ok": False, "object": None}

        users: list = []
        try:
            for obj in self.doc.objects():
                try:
                    slots = obj.material_slots
                except Exception:
                    continue
                for slot in slots:
                    try:
                        mat = slot.material
                    except Exception:
                        mat = None
                    if mat is not None and mat.name_full == name:
                        users.append(obj)
                        break
        except Exception:
            users = []

        try:
            for o in self.doc.selected_objects():
                o.select_set(False)
        except Exception:
            pass

        first = None
        for obj in users:
            try:
                obj.select_set(True)
                if first is None:
                    first = obj
            except Exception:
                continue

        if first is None:
            return {"ok": True, "object": None}

        try:
            for idx, slot in enumerate(first.material_slots):
                try:
                    mat = slot.material
                except Exception:
                    mat = None
                if mat is not None and mat.name_full == name:
                    first.active_material_index = idx
                    break
        except Exception:
            pass

        try:
            self.bpy.context.view_layer.objects.active = first
        except Exception:
            pass
        self._view_selected()
        self.doc.tag_redraw()
        return {"ok": True, "object": first.name}

    def delete_material(self, name: str, include_hidden: bool = False) -> int:
        used_any, used_visible = self._scene_material_usage()
        protected = used_visible if include_hidden else used_any
        targets: list = []
        try:
            for m in self.bpy.data.materials:
                try:
                    if m.name_full == name and m.name_full not in protected:
                        targets.append(m)
                except Exception:
                    continue
        except Exception:
            return 0
        if not targets:
            return 0

        removed = 0
        for m in targets:
            try:
                self.bpy.data.materials.remove(m)
                removed += 1
            except Exception:
                continue
        if removed:
            self.doc.undo_push("Delete material '%s'" % name)
            self.doc.tag_redraw()
        return removed

    def delete_unused_materials(self, include_hidden: bool = False,
                                accepted=None) -> int:
        accepted = set(accepted or ())
        used_any, used_visible = self._scene_material_usage()
        protected = used_visible if include_hidden else used_any
        targets: list = []
        try:
            for m in self.bpy.data.materials:
                try:
                    name = m.name_full
                except Exception:
                    continue
                if name in protected or name in accepted:
                    continue
                if self._is_internal_material(name):
                    continue
                targets.append(m)
        except Exception:
            return 0
        if not targets:
            return 0

        removed = 0
        for m in targets:
            try:
                self.bpy.data.materials.remove(m)
                removed += 1
            except Exception:
                continue
        if removed:
            self.doc.undo_push("Delete %d unused material(s)" % removed)
            self.doc.tag_redraw()
        return removed
