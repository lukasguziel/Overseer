from __future__ import annotations

import os

import c4d

from ..core.materials.base import MaterialsBase
from .scene.readers import editor_hidden


class CinemaMaterials(MaterialsBase):

    @staticmethod
    def _mat_key(m):
        try:
            return m.GetGUID()
        except Exception:
            try:
                return m.GetName()
            except Exception:
                return id(m)

    def _material_usage(self) -> tuple[set, set]:
        used_any: set = set()
        used_visible: set = set()

        def visit(op, hidden_anc):
            while op:
                hidden = editor_hidden(op, hidden_anc)
                try:
                    for tag in op.GetTags():
                        if tag.IsInstanceOf(c4d.Ttexture):
                            m = tag.GetMaterial()
                            if m is not None:
                                key = self._mat_key(m)
                                used_any.add(key)
                                if not hidden:
                                    used_visible.add(key)
                except Exception:
                    pass
                visit(op.GetDown(), hidden)
                op = op.GetNext()

        visit(self.doc.GetFirstObject(), False)
        return used_any, used_visible

    def _used_material_keys(self) -> set:
        return self._material_usage()[0]

    def _used_material_names(self) -> set:
        used = self._used_material_keys()
        out: set = set()
        try:
            for m in self.doc.GetMaterials():
                if self._mat_key(m) in used:
                    out.add(m.GetName())
        except Exception:
            pass
        return out

    def _all_material_names(self) -> set:
        try:
            return {m.GetName() for m in self.doc.GetMaterials()}
        except Exception:
            return set()

    def get_materials(self) -> list:
        return self.doc.GetMaterials()

    def get_material_name(self, mat):
        return mat.GetName()

    def get_material_key(self, mat):
        return self._mat_key(mat)

    def get_material_usage(self) -> tuple:
        return self._material_usage()

    def get_missing_textures(self, mat, name: str) -> list:
        doc_path = self.doc.GetDocumentPath() or ""
        out: list = []
        for sh in self._iter_bitmap_shaders(mat):
            try:
                fn = sh[c4d.BITMAPSHADER_FILENAME]
                if not fn:
                    continue
                resolved = c4d.GenerateTexturePath(doc_path, fn, "")
                if not resolved or not os.path.isfile(resolved):
                    out.append({"material": name,
                                "file": os.path.basename(str(fn))})
            except Exception:
                continue
        return out

    def focus_material(self, name: str) -> dict:
        target = None
        try:
            for m in self.doc.GetMaterials():
                if m.GetName() == name:
                    target = m
                    break
        except Exception:
            target = None
        if target is None:
            return {"ok": False, "object": None}
        try:
            self.doc.SetActiveMaterial(target)
            c4d.EventAdd()
        except Exception:
            pass
        for guid in sorted(self._by_guid):
            op = self._by_guid[guid]
            for tag in op.GetTags():
                try:
                    if (tag.IsInstanceOf(c4d.Ttexture)
                            and tag[c4d.TEXTURETAG_MATERIAL] == target):
                        self.focus(guid)
                        return {"ok": True, "object": op.GetName()}
                except Exception:
                    continue
        return {"ok": True, "object": None}

    def delete_material(self, name: str, include_hidden: bool = False) -> int:
        doc = self.doc
        used_any, used_visible = self._material_usage()
        protected = used_visible if include_hidden else used_any
        targets = [m for m in doc.GetMaterials()
                   if m.GetName() == name and self._mat_key(m) not in protected]
        if not targets:
            return 0

        doc.StartUndo()
        for m in targets:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, m)
            m.Remove()
        doc.EndUndo()
        c4d.EventAdd()
        return len(targets)

    def delete_unused_materials(self, include_hidden: bool = False,
                                accepted: set | None = None) -> int:
        doc = self.doc
        accepted = accepted or set()
        used_any, used_visible = self._material_usage()
        protected = used_visible if include_hidden else used_any
        targets = [m for m in doc.GetMaterials()
                   if self._mat_key(m) not in protected
                   and m.GetName() not in accepted
                   and not self.is_internal(m.GetName())]
        if not targets:
            return 0

        doc.StartUndo()
        for m in targets:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, m)
            m.Remove()
        doc.EndUndo()
        c4d.EventAdd()
        return len(targets)
