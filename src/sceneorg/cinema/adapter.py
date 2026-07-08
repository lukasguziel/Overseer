from __future__ import annotations

import collections

import c4d

from ..core import model
from ..core.ops import LayerOp, RenameOp, ReparentOp

LAYER_COLORS = {
    "Lights": (0.98, 0.75, 0.14),
    "Cameras": (0.22, 0.74, 0.97),
    "Proxies": (0.69, 0.48, 1.0),
    "Splines": (0.55, 0.60, 0.70),
}

KNOWN_TYPES = {
    c4d.Onull: "Null",
    c4d.Ocamera: "Camera",
    c4d.Olight: "Light",
    c4d.Opolygon: "Mesh",
    c4d.Ospline: "Spline",
    c4d.Oinstance: "Instance",
    1018544: "MoGraph Cloner",
    1018545: "MoGraph Matrix",
    1018791: "MoGraph Fracture",
    1019268: "MoGraph Text",
}

RS_LIGHT_IDS = {1036751}
RS_CAMERA_IDS = {1057516}


def type_name(op) -> str:
    t = op.GetType()
    if t in KNOWN_TYPES:
        return KNOWN_TYPES[t]
    try:
        n = op.GetTypeName()
        if n:
            return n
    except Exception:
        pass
    return "type_%d" % t


def _virtual_geo(op) -> tuple:
    pts = polys = 0
    o = op
    while o:
        if o.IsInstanceOf(c4d.Opolygon):
            try:
                pts += o.GetPointCount()
                polys += o.GetPolygonCount()
            except Exception:
                pass
        dc = o.GetDeformCache()
        if dc:
            p2, q2 = _virtual_geo(dc)
            pts += p2
            polys += q2
        c = o.GetCache()
        if c:
            p2, q2 = _virtual_geo(c)
            pts += p2
            polys += q2
        down = o.GetDown()
        if down:
            p2, q2 = _virtual_geo(down)
            pts += p2
            polys += q2
        o = o.GetNext()
    return pts, polys


def own_geo(op) -> tuple:
    if op.IsInstanceOf(c4d.Opolygon):
        try:
            return op.GetPointCount(), op.GetPolygonCount()
        except Exception:
            return 0, 0
    cache = op.GetDeformCache() or op.GetCache()
    if cache is None:
        return 0, 0
    return _virtual_geo(cache)


def classify(op) -> str:
    t = op.GetType()
    if op.CheckType(c4d.Ocamera) or t in RS_CAMERA_IDS:
        return model.CAT_CAMERA
    if op.CheckType(c4d.Olight) or t in RS_LIGHT_IDS:
        return model.CAT_LIGHT
    tn = type_name(op).lower()
    if "light" in tn or "licht" in tn:
        return model.CAT_LIGHT
    if "camera" in tn or "kamera" in tn:
        return model.CAT_CAMERA
    if op.CheckType(c4d.Onull):
        return model.CAT_NULL
    if op.CheckType(c4d.Ospline):
        return model.CAT_SPLINE
    if op.CheckType(c4d.Opolygon):
        return model.CAT_MESH
    return model.CAT_OTHER


def layer_name(op) -> str | None:
    try:
        lay = op.GetLayerObject(op.GetDocument())
        return lay.GetName() if lay is not None else None
    except Exception:
        return None


def editor_hidden(op) -> bool:
    try:
        return op[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] == c4d.MODE_OFF
    except Exception:
        return False


class SceneAdapter:

    def __init__(self, doc) -> None:
        self.doc = doc
        self._by_guid: dict[int, object] = {}
        self._selected_direct: set = set()
        self._selected_subtree: set = set()

    def count_objects(self) -> int:
        n = 0
        stack = []
        op = self.doc.GetFirstObject()
        while op or stack:
            if op is None:
                op = stack.pop()
            n += 1
            down = op.GetDown()
            nxt = op.GetNext()
            if down and nxt:
                stack.append(nxt)
            op = down or nxt
        return n

    def build_tree(self, progress=None) -> model.SceneTree:
        self._by_guid.clear()
        self._selected_direct.clear()
        self._selected_subtree.clear()
        tree = model.SceneTree()
        counter = [0]
        total = self.count_objects() if progress else 0

        def make(op, parent, depth, sel_ancestor, hidden_ancestor):
            guid = counter[0]
            counter[0] += 1
            if progress and counter[0] % 50 == 0:
                progress(counter[0], total, op.GetName())
            pts, polys = own_geo(op)
            hidden = hidden_ancestor or editor_hidden(op)
            node = model.SceneNode(
                name=op.GetName(),
                type_name=type_name(op),
                category=classify(op),
                guid=guid,
                depth=depth,
                point_count=pts,
                poly_count=polys,
                visible=not hidden,
                layer=layer_name(op),
            )
            self._by_guid[guid] = op
            is_sel = bool(op.GetBit(c4d.BIT_ACTIVE))
            in_scope = sel_ancestor or is_sel
            if is_sel:
                self._selected_direct.add(guid)
            if in_scope:
                self._selected_subtree.add(guid)
            child = op.GetDown()
            while child:
                node.add_child(make(child, node, depth + 1, in_scope, hidden))
                child = child.GetNext()
            return node

        top = self.doc.GetFirstObject()
        while top:
            tree.roots.append(make(top, None, 0, False, False))
            top = top.GetNext()
        return tree

    def selected_guids(self, include_children: bool = True) -> set:
        return set(self._selected_subtree if include_children
                   else self._selected_direct)

    def focus(self, guid: int) -> bool:
        op = self._by_guid.get(guid)
        if op is None:
            return False
        self.doc.SetActiveObject(op, c4d.SELECTION_NEW)

        up = op.GetUp()
        while up is not None:
            up.SetBit(c4d.BIT_OFOLD)
            up = up.GetUp()
        try:
            c4d.CallCommand(100004769)
        except Exception:
            pass

        bd = self.doc.GetActiveBaseDraw()
        cam = None
        if bd is not None:
            cam = bd.GetSceneCamera(self.doc) or bd.GetEditorCamera()
        if cam is not None:
            mg = op.GetMg()
            center = mg * op.GetMp()
            rad = op.GetRad()
            sx, sy, sz = mg.v1.GetLength(), mg.v2.GetLength(), mg.v3.GetLength()
            r = max(rad.x * sx, rad.y * sy, rad.z * sz)
            if r <= 0:
                r = 100.0
            cm = cam.GetMg()
            forward = cm.v3
            dist = r * 2.8
            cm.off = center - forward * dist
            cam.SetMg(cm)

        c4d.EventAdd()
        try:
            c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
        except Exception:
            pass
        return True

    def _used_material_names(self) -> set:
        used_names: set = set()

        def visit(op):
            while op:
                try:
                    for tag in op.GetTags():
                        if tag.IsInstanceOf(c4d.Ttexture):
                            m = tag.GetMaterial()
                            if m is not None:
                                used_names.add(m.GetName())
                except Exception:
                    pass
                visit(op.GetDown())
                op = op.GetNext()

        visit(self.doc.GetFirstObject())
        return used_names

    def scan_materials(self) -> dict:
        import os
        doc = self.doc
        try:
            mats = doc.GetMaterials()
        except Exception:
            return {"total": 0, "unused": [], "missing": [], "missing_textures": 0}

        used_names = self._used_material_names()
        doc_path = doc.GetDocumentPath() or ""
        unused: list = []
        missing: list = []
        for m in mats:
            name = m.GetName()
            if name not in used_names:
                unused.append(name)
            try:
                sh = m.GetFirstShader()
                while sh:
                    if sh.IsInstanceOf(c4d.Xbitmap):
                        fn = sh[c4d.BITMAPSHADER_FILENAME]
                        if fn:
                            resolved = c4d.GenerateTexturePath(doc_path, fn, "")
                            if not resolved or not os.path.isfile(resolved):
                                missing.append({"material": name,
                                                "file": os.path.basename(str(fn))})
                    sh = sh.GetNext()
            except Exception:
                pass

        return {
            "total": len(mats),
            "unused": unused,
            "missing": missing[:50],
            "missing_textures": len(missing),
        }

    def _iter_bitmap_shaders(self, mat):
        def walk(sh):
            while sh:
                try:
                    if sh.IsInstanceOf(c4d.Xbitmap):
                        yield sh
                    down = sh.GetDown()
                except Exception:
                    down = None
                if down:
                    yield from walk(down)
                sh = sh.GetNext()
        try:
            yield from walk(mat.GetFirstShader())
        except Exception:
            return

    def scan_textures(self) -> dict:
        import os

        from ..core import imagesize
        doc = self.doc
        doc_path = doc.GetDocumentPath() or ""
        used_names = self._used_material_names()
        entries: list = []
        seen: set = set()
        meta_cache: dict = {}
        try:
            mats = doc.GetMaterials()
        except Exception:
            mats = []

        def file_meta(path):
            if path in meta_cache:
                return meta_cache[path]
            size = 0
            dims = None
            try:
                size = os.path.getsize(path)
            except Exception:
                size = 0
            dims = imagesize.image_size(path)
            meta_cache[path] = (size, dims)
            return meta_cache[path]

        for m in mats:
            name = m.GetName()
            used = name in used_names
            for sh in self._iter_bitmap_shaders(m):
                try:
                    raw = sh[c4d.BITMAPSHADER_FILENAME]
                except Exception:
                    raw = None
                if not raw:
                    continue
                raw = str(raw)
                key = (name, raw)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    resolved = c4d.GenerateTexturePath(doc_path, raw, "") or ""
                except Exception:
                    resolved = ""
                exists = bool(resolved) and os.path.isfile(resolved)
                absolute = os.path.isabs(raw)
                relocatable = False
                rel_target = ""
                if absolute and exists and doc_path:
                    try:
                        rp = os.path.relpath(resolved, doc_path)
                        if not rp.startswith(".."):
                            relocatable = True
                            rel_target = rp.replace("\\", "/")
                    except Exception:
                        pass
                disk_bytes = 0
                width = height = 0
                res_tag = ""
                if exists:
                    disk_bytes, dims = file_meta(resolved)
                    if dims:
                        width, height = dims
                        res_tag = imagesize.resolution_tag(max(width, height))
                entries.append({
                    "material": name,
                    "used": used,
                    "file": os.path.basename(raw),
                    "path": raw,
                    "resolved": resolved,
                    "absolute": absolute,
                    "exists": exists,
                    "missing": not exists,
                    "relocatable": relocatable,
                    "rel_target": rel_target,
                    "bytes": disk_bytes,
                    "width": width,
                    "height": height,
                    "res_tag": res_tag,
                })
        absolute = [e for e in entries if e["absolute"]]
        relative = [e for e in entries if not e["absolute"]]
        total_bytes = sum(size for size, _ in meta_cache.values())
        return {
            "doc_path": doc_path,
            "total": len(entries),
            "absolute_count": len(absolute),
            "relative_count": len(relative),
            "missing_count": sum(1 for e in entries if e["missing"]),
            "relocatable_count": sum(1 for e in entries if e["relocatable"]),
            "total_bytes": total_bytes,
            "absolute": absolute,
            "relative": relative,
        }

    def make_textures_relative(self, materials: list | None = None) -> dict:
        import os
        doc = self.doc
        doc_path = doc.GetDocumentPath() or ""
        if not doc_path:
            return {"fixed": 0, "error": "Project is not saved (no folder to make paths relative to)."}
        only = set(materials) if materials else None
        targets: list = []
        for m in doc.GetMaterials():
            if only is not None and m.GetName() not in only:
                continue
            for sh in self._iter_bitmap_shaders(m):
                try:
                    raw = str(sh[c4d.BITMAPSHADER_FILENAME] or "")
                except Exception:
                    continue
                if not raw or not os.path.isabs(raw):
                    continue
                try:
                    resolved = c4d.GenerateTexturePath(doc_path, raw, "") or raw
                except Exception:
                    resolved = raw
                if not os.path.isfile(resolved):
                    continue
                try:
                    rp = os.path.relpath(resolved, doc_path)
                except Exception:
                    continue
                if rp.startswith(".."):
                    continue
                targets.append((sh, rp.replace("\\", "/")))
        if not targets:
            return {"fixed": 0}

        doc.StartUndo()
        for sh, rp in targets:
            doc.AddUndo(c4d.UNDOTYPE_CHANGE, sh)
            sh[c4d.BITMAPSHADER_FILENAME] = rp
        doc.EndUndo()
        c4d.EventAdd()
        return {"fixed": len(targets)}

    def scan_layers(self) -> list[dict]:
        out: list[dict] = []
        try:
            root = self.doc.GetLayerObjectRoot()
        except Exception:
            return out
        lay = root.GetDown() if root is not None else None
        while lay:
            entry = {"name": lay.GetName(), "color": None,
                     "solo": False, "view": True, "render": True,
                     "locked": False}
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

    def delete_material(self, name: str) -> int:
        doc = self.doc
        used_names = self._used_material_names()
        if name in used_names:
            return 0
        targets = [m for m in doc.GetMaterials() if m.GetName() == name]
        if not targets:
            return 0

        doc.StartUndo()
        for m in targets:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, m)
            m.Remove()
        doc.EndUndo()
        c4d.EventAdd()
        return len(targets)

    def delete_unused_materials(self) -> int:
        doc = self.doc
        used_names = self._used_material_names()
        targets = [m for m in doc.GetMaterials() if m.GetName() not in used_names]
        if not targets:
            return 0

        doc.StartUndo()
        for m in targets:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, m)
            m.Remove()
        doc.EndUndo()
        c4d.EventAdd()
        return len(targets)

    def _match_group(self, obj, segment: str, canonical=None) -> bool:
        if not obj.CheckType(c4d.Onull):
            return False
        name = obj.GetName()
        if name.lower() == segment.lower():
            return True
        return canonical is not None and canonical(name) == segment

    def ensure_group_path(self, path: str, created: list[object],
                          canonical=None) -> object:
        parent = None
        for segment in path.split("/"):
            found = None
            child = parent.GetDown() if parent is not None \
                else self.doc.GetFirstObject()
            while child:
                if self._match_group(child, segment, canonical):
                    found = child
                    break
                child = child.GetNext()
            if found is None:
                found = c4d.BaseObject(c4d.Onull)
                found.SetName(segment)
                if parent is not None:
                    found.InsertUnderLast(parent)
                else:
                    self.doc.InsertObject(found)
                self.doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, found)
                created.append(found)
            parent = found
        return parent

    def _find_or_create_group(self, name: str, created: list[object]) -> object:
        return self.ensure_group_path(name, created)

    def apply_renames(self, renames: list[RenameOp]) -> int:
        if not renames:
            return 0
        self.doc.StartUndo()
        count = 0
        for op in renames:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetName(op.new_name)
            count += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

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

    def apply_layers(self, layerops: list[LayerOp]) -> int:
        if not layerops:
            return 0
        self.doc.StartUndo()
        created: list = []
        cache: dict = {}
        count = 0
        for op in layerops:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            layer = self._find_or_create_layer(op.layer, created, cache)
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetLayerObject(layer)
            count += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    def _do_reparents(self, reparents: list[ReparentOp], created: list,
                      canonical=None) -> int:
        count = 0
        for op in reparents:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            group = self.ensure_group_path(op.to_group, created, canonical)
            if obj == group:
                continue
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            mg = obj.GetMg()
            obj.Remove()
            obj.InsertUnderLast(group)
            obj.SetMg(mg)
            count += 1
        return count

    def apply_reparents(self, reparents: list[ReparentOp], canonical=None) -> int:
        if not reparents:
            return 0
        self.doc.StartUndo()
        created: list[object] = []
        count = self._do_reparents(reparents, created, canonical)
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    def apply_bundle(self, renames: list[RenameOp],
                     reparents: list[ReparentOp],
                     layerops: list[LayerOp],
                     canonical=None) -> dict:
        if not (renames or reparents or layerops):
            return {"renames": 0, "reparents": 0, "layers": 0}
        self.doc.StartUndo()
        created: list = []
        lay_cache: dict = {}
        renamed = 0
        for op in renames:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetName(op.new_name)
            renamed += 1
        reparented = self._do_reparents(reparents, created, canonical)
        layered = 0
        for op in layerops:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            layer = self._find_or_create_layer(op.layer, created, lay_cache)
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetLayerObject(layer)
            layered += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"renames": renamed, "reparents": reparented, "layers": layered}

    def apply_plan(self, operations: list[dict]) -> dict:
        refs: dict = {}
        created: list = []
        lay_cache: dict = {}
        applied: collections.Counter = collections.Counter()
        errors: list = []

        def resolve(ref):
            if ref is None:
                return None
            if isinstance(ref, str) and ref.startswith("$"):
                return refs.get(ref)
            return self._by_guid.get(ref)

        self.doc.StartUndo()
        for i, opd in enumerate(operations):
            kind = opd.get("op")
            try:
                if kind == "group":
                    null = c4d.BaseObject(c4d.Onull)
                    null.SetName(opd.get("name", "GROUP"))
                    parent = resolve(opd.get("under"))
                    if parent is not None:
                        null.InsertUnderLast(parent)
                    else:
                        self.doc.InsertObject(null)
                    self.doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, null)
                    created.append(null)
                    if opd.get("id"):
                        refs[opd["id"]] = null
                    applied["group"] += 1
                elif kind == "rename":
                    obj = resolve(opd.get("target"))
                    if obj is None:
                        errors.append("rename #%d: target missing" % i)
                        continue
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    obj.SetName(opd.get("to", obj.GetName()))
                    applied["rename"] += 1
                elif kind == "move":
                    obj = resolve(opd.get("target"))
                    dest = resolve(opd.get("into"))
                    if obj is None:
                        errors.append("move #%d: target missing" % i)
                        continue
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    mg = obj.GetMg()
                    obj.Remove()
                    if dest is not None:
                        obj.InsertUnderLast(dest)
                    else:
                        self.doc.InsertObject(obj)
                    obj.SetMg(mg)
                    applied["move"] += 1
                elif kind == "layer":
                    obj = resolve(opd.get("target"))
                    if obj is None:
                        errors.append("layer #%d: target missing" % i)
                        continue
                    layer = self._find_or_create_layer(
                        opd.get("layer", "Layer"), created, lay_cache)
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    obj.SetLayerObject(layer)
                    applied["layer"] += 1
                else:
                    errors.append("op #%d: unknown '%s'" % (i, kind))
            except Exception as ex:  # noqa: BLE001
                errors.append("op #%d (%s): %s" % (i, kind, ex))
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"applied": dict(applied), "errors": errors,
                "total": sum(applied.values())}
