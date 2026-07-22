from __future__ import annotations

import c4d

from ..core.materials import logic as mat_logic
from .scene.readers import editor_hidden


class MaterialOps:

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

    def scan_materials(self, include_hidden: bool = True,
                       accepted: set | None = None) -> dict:
        import os
        accepted = accepted or set()
        doc = self.doc
        try:
            mats = doc.GetMaterials()
        except Exception:
            return mat_logic.scan_result(0, [], [], [], accepted, [])

        from ..core.materials.logic import is_internal_material

        used_any, used_visible = self._material_usage()
        doc_path = doc.GetDocumentPath() or ""
        unused: list = []
        only_hidden: list = []
        accepted_out: list = []
        missing: list = []
        for m in mats:
            name = m.GetName()
            if is_internal_material(name):
                continue
            key = self._mat_key(m)
            nowhere = key not in used_any
            hidden_only = (not nowhere) and key not in used_visible
            if nowhere or (hidden_only and include_hidden):
                if name in accepted:
                    accepted_out.append(name)
                else:
                    unused.append(name)
                    if hidden_only:
                        only_hidden.append(name)
            for sh in self._iter_bitmap_shaders(m):
                try:
                    fn = sh[c4d.BITMAPSHADER_FILENAME]
                    if not fn:
                        continue
                    resolved = c4d.GenerateTexturePath(doc_path, fn, "")
                    if not resolved or not os.path.isfile(resolved):
                        missing.append({"material": name,
                                        "file": os.path.basename(str(fn))})
                except Exception:
                    continue

        return mat_logic.scan_result(len(mats), unused, only_hidden,
                                      accepted_out, accepted, missing)

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
        from ..core.materials.logic import is_internal_material
        doc = self.doc
        accepted = accepted or set()
        used_any, used_visible = self._material_usage()
        protected = used_visible if include_hidden else used_any
        targets = [m for m in doc.GetMaterials()
                   if self._mat_key(m) not in protected
                   and m.GetName() not in accepted
                   and not is_internal_material(m.GetName())]
        if not targets:
            return 0

        doc.StartUndo()
        for m in targets:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, m)
            m.Remove()
        doc.EndUndo()
        c4d.EventAdd()
        return len(targets)
