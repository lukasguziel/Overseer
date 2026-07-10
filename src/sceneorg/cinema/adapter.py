from __future__ import annotations

import collections

import c4d

from ..core import journal as journalmod
from ..core import model
from ..core.defaults import LAYER_COLORS, RS_CAMERA_IDS, RS_LIGHT_IDS
from ..core.ops import LayerOp, RenameOp, ReparentOp
from .constants import DOC_JOURNAL_ID, KNOWN_TYPES


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


def stable_id(op) -> int:
    try:
        return op.GetGUID()
    except Exception:
        return 0


def editor_hidden(op) -> bool:
    try:
        return op[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] == c4d.MODE_OFF
    except Exception:
        return False


class SceneAdapter:

    def __init__(self, doc) -> None:
        self.doc = doc
        self._by_guid: dict[int, object] = {}
        self._by_sid: dict[int, object] = {}
        self._selected_direct: set = set()
        self._selected_subtree: set = set()
        self.last_changes: list[dict] = []

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
        self._by_sid.clear()
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
            self._by_sid[stable_id(op)] = op
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
                hidden = hidden_anc or editor_hidden(op)
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
            return {"total": 0, "unused": [], "only_hidden": [], "accepted": [],
                    "deletable_count": 0, "missing": [], "missing_textures": 0}

        used_any, used_visible = self._material_usage()
        doc_path = doc.GetDocumentPath() or ""
        unused: list = []
        only_hidden: list = []
        accepted_out: list = []
        missing: list = []
        for m in mats:
            name = m.GetName()
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
            "only_hidden": only_hidden,
            "accepted": accepted_out,
            "accepted_all": sorted(accepted),
            "deletable_count": len(unused),
            "missing": missing[:50],
            "missing_textures": len(missing),
        }

    def material_previews(self, names=None, size=48, progress=None):
        import base64
        import os
        import tempfile

        only = set(names) if names else None
        out = {}
        tmp = os.path.join(tempfile.gettempdir(), "so_matprev.png")
        try:
            mats = self.doc.GetMaterials()
        except Exception:
            return out
        wanted = [m for m in mats
                  if only is None or m.GetName() in only]
        for i, m in enumerate(wanted):
            name = m.GetName()
            if progress:
                progress(i, len(wanted), name)
            try:
                bmp = m.GetPreview(0)
                if bmp is None:
                    continue
                w, h = bmp.GetSize()
                if w <= 0 or h <= 0:
                    continue
                if w != size or h != size:
                    dst = c4d.bitmaps.BaseBitmap()
                    if dst.Init(size, size, 32) != c4d.IMAGERESULT_OK:
                        continue
                    bmp.ScaleIt(dst, 256, True, True)
                    bmp = dst
                if bmp.Save(tmp, c4d.FILTER_PNG) != c4d.IMAGERESULT_OK:
                    continue
                with open(tmp, "rb") as f:
                    data = base64.b64encode(f.read()).decode("ascii")
                out[name] = "data:image/png;base64," + data
            except Exception:
                continue
        try:
            os.remove(tmp)
        except Exception:
            pass
        return out

    def texture_previews(self, paths=None, size=40, progress=None):
        import base64
        import os
        import tempfile

        out = {}
        tmp = os.path.join(tempfile.gettempdir(), "so_texprev.png")
        all_paths = list(paths or [])
        for i, p in enumerate(all_paths):
            if progress:
                progress(i, len(all_paths), os.path.basename(str(p or "")))
            try:
                if not p or not os.path.isfile(p):
                    continue
                bmp = c4d.bitmaps.BaseBitmap()
                if bmp.InitWith(p)[0] != c4d.IMAGERESULT_OK:
                    continue
                w, h = bmp.GetSize()
                if w <= 0 or h <= 0:
                    continue
                dst = c4d.bitmaps.BaseBitmap()
                if dst.Init(size, size, 32) != c4d.IMAGERESULT_OK:
                    continue
                bmp.ScaleIt(dst, 256, True, True)
                if dst.Save(tmp, c4d.FILTER_PNG) != c4d.IMAGERESULT_OK:
                    continue
                with open(tmp, "rb") as f:
                    data = base64.b64encode(f.read()).decode("ascii")
                out[p] = "data:image/png;base64," + data
            except Exception:
                continue
        try:
            os.remove(tmp)
        except Exception:
            pass
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

    _TEX_EXTS = frozenset({
        ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".hdr", ".tga",
        ".psd", ".bmp", ".gif", ".iff", ".dds", ".webp", ".pict", ".pct",
        ".rla", ".rpf", ".dpx", ".sgi", ".rgb", ".b3d", ".ies", ".tx",
    })

    def _is_texture_file(self, path: str) -> bool:
        import os
        ext = os.path.splitext(path)[1].lower()
        return ext in self._TEX_EXTS

    def _owner_material_name(self, owner):
        if owner is None:
            return ""
        try:
            if owner.IsInstanceOf(c4d.Mbase):
                return owner.GetName()
        except Exception:
            pass
        try:
            main = owner.GetMain()
            if main is not None:
                return main.GetName()
        except Exception:
            pass
        try:
            return owner.GetName()
        except Exception:
            return ""

    def _texture_refs(self, effective_used: set | None = None) -> list:
        doc = self.doc
        used_names = (effective_used if effective_used is not None
                      else self._used_material_names())
        all_names = self._all_material_names()
        refs: list = []
        seen: set = set()
        assets: list = []
        try:
            flags = getattr(c4d, "ASSETDATA_FLAG_TEXTURESONLY",
                            getattr(c4d, "ASSETDATA_FLAG_0", 0))
            filled: list = []
            c4d.documents.GetAllAssetsNew(doc, False, "", flags, filled)
            assets = [a for a in filled if isinstance(a, dict)]
        except Exception:
            assets = []
        for a in assets:
            try:
                raw = str(a.get("filename") or "")
            except Exception:
                raw = ""
            if not raw or not self._is_texture_file(raw):
                continue
            name = self._owner_material_name(a.get("owner")) \
                or str(a.get("assetname") or "")
            key = (name, raw)
            if key in seen:
                continue
            seen.add(key)
            used = name in used_names or name not in all_names
            refs.append((name, raw, used))
        if refs:
            return refs
        try:
            mats = doc.GetMaterials()
        except Exception:
            mats = []
        for m in mats:
            name = m.GetName()
            used = name in used_names
            for sh in self._iter_bitmap_shaders(m):
                try:
                    raw = str(sh[c4d.BITMAPSHADER_FILENAME] or "")
                except Exception:
                    raw = ""
                if not raw:
                    continue
                key = (name, raw)
                if key in seen:
                    continue
                seen.add(key)
                refs.append((name, raw, used))
        return refs

    def scan_textures(self, include_hidden: bool = True) -> dict:
        import os

        from ..core import imagesize
        from ..core import textures as texmod
        doc = self.doc
        doc_path = doc.GetDocumentPath() or ""
        used_any, used_visible = self._material_usage()
        effective_keys = used_any if include_hidden else used_visible
        effective: set = set()
        try:
            for m in doc.GetMaterials():
                if self._mat_key(m) in effective_keys:
                    effective.add(m.GetName())
        except Exception:
            pass
        entries: list = []
        meta_cache: dict = {}

        def file_meta(path):
            if path in meta_cache:
                return meta_cache[path]
            size = 0
            try:
                size = os.path.getsize(path)
            except Exception:
                size = 0
            info = texmod.analyze_image(path)
            meta_cache[path] = (size, info)
            return meta_cache[path]

        for name, raw, used in self._texture_refs(effective):
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
            info = None
            if exists:
                disk_bytes, info = file_meta(resolved)
                if info is not None:
                    width, height = info.width, info.height
                    res_tag = imagesize.resolution_tag(max(width, height))
            entry = {
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
                "bit_depth": info.bit_depth if info else 0,
                "channels": info.channels if info else 0,
                "has_alpha": bool(info.has_alpha) if info else False,
                "greyscale": bool(info.greyscale) if info else False,
                "colorspace": info.colorspace if info else "",
                "vram": texmod.vram_bytes(width, height) if info else 0,
            }
            entries.append(entry)
        absolute = [e for e in entries if e["absolute"]]
        relative = [e for e in entries if not e["absolute"]]
        total_bytes = sum(size for size, _ in meta_cache.values())
        total_vram = sum(texmod.vram_bytes(info.width, info.height)
                         for _size, info in meta_cache.values()
                         if info is not None)
        return {
            "doc_path": doc_path,
            "total": len(entries),
            "absolute_count": len(absolute),
            "relative_count": len(relative),
            "missing_count": sum(1 for e in entries if e["missing"]),
            "relocatable_count": sum(1 for e in entries if e["relocatable"]),
            "total_bytes": total_bytes,
            "total_vram": total_vram,
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

    def collect_textures(self, materials: list | None = None,
                         subdir: str = "tex") -> dict:
        import os
        import shutil
        doc = self.doc
        doc_path = doc.GetDocumentPath() or ""
        if not doc_path:
            return {"copied": 0, "relinked": 0, "skipped": 0,
                    "error": "Project is not saved (nowhere to copy to)."}
        subdir = (subdir or "tex").strip().strip("/\\")
        if not subdir or os.path.isabs(subdir) or ".." in subdir.split("/") \
                or ".." in subdir.split("\\"):
            subdir = "tex"
        target_dir = os.path.join(doc_path, subdir)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as ex:
            return {"copied": 0, "relinked": 0, "skipped": 0,
                    "error": "Cannot create %s: %s" % (target_dir, ex)}

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
                    rp = ".."
                if not rp.startswith(".."):
                    continue
                targets.append((sh, resolved))
        if not targets:
            return {"copied": 0, "relinked": 0, "skipped": 0}

        copied = relinked = skipped = 0
        dest_by_src: dict = {}
        used_names: set = set()
        try:
            used_names = {fn.lower() for fn in os.listdir(target_dir)}
        except OSError:
            pass

        def dest_for(src: str) -> str | None:
            if src in dest_by_src:
                return dest_by_src[src]
            base = os.path.basename(src)
            dst = os.path.join(target_dir, base)
            try:
                if os.path.isfile(dst):
                    if os.path.getsize(dst) == os.path.getsize(src):
                        dest_by_src[src] = dst
                        return dst
                    stem, ext = os.path.splitext(base)
                    n = 1
                    while True:
                        cand = "%s_%d%s" % (stem, n, ext)
                        if cand.lower() not in used_names and \
                                not os.path.isfile(os.path.join(target_dir, cand)):
                            dst = os.path.join(target_dir, cand)
                            break
                        n += 1
                shutil.copy2(src, dst)
                used_names.add(os.path.basename(dst).lower())
                dest_by_src[src] = dst
                return dst
            except OSError:
                return None

        doc.StartUndo()
        for sh, src in targets:
            dst = dest_for(src)
            if dst is None:
                skipped += 1
                continue
            rel = subdir.replace("\\", "/") + "/" + os.path.basename(dst)
            try:
                doc.AddUndo(c4d.UNDOTYPE_CHANGE, sh)
                sh[c4d.BITMAPSHADER_FILENAME] = rel
                relinked += 1
            except Exception:
                skipped += 1
        doc.EndUndo()
        copied = len(dest_by_src)
        c4d.EventAdd()
        return {"copied": copied, "relinked": relinked, "skipped": skipped,
                "target": target_dir}

    @staticmethod
    def _same_path(a: str, b: str) -> bool:
        import os
        na = os.path.normcase(os.path.normpath((a or "").strip()))
        nb = os.path.normcase(os.path.normpath((b or "").strip()))
        return bool(na) and na == nb

    def _find_path_params(self, owner, raw: str) -> list:
        holders = [owner]
        try:
            first = owner.GetFirstShader()
        except Exception:
            first = None
        stack = [first] if first is not None else []
        while stack:
            sh = stack.pop()
            while sh is not None:
                holders.append(sh)
                try:
                    down = sh.GetDown()
                except Exception:
                    down = None
                if down is not None:
                    stack.append(down)
                sh = sh.GetNext()

        out: list = []
        for holder in holders:
            try:
                if holder.CheckType(c4d.Xbitmap) and self._same_path(
                        str(holder[c4d.BITMAPSHADER_FILENAME] or ""), raw):
                    out.append((holder, c4d.BITMAPSHADER_FILENAME))
                    continue
            except Exception:
                pass
            try:
                description = holder.GetDescription(c4d.DESCFLAGS_DESC_NONE)
                for _bc, paramid, _group in description:
                    try:
                        val = holder[paramid]
                    except Exception:
                        continue
                    if isinstance(val, str) and self._same_path(val, raw):
                        out.append((holder, paramid))
            except Exception:
                continue
        return out

    def _all_material_holders(self):
        try:
            mats = self.doc.GetMaterials()
        except Exception:
            mats = []
        for m in mats:
            yield m
            try:
                first = m.GetFirstShader()
            except Exception:
                first = None
            stack = [first] if first is not None else []
            while stack:
                sh = stack.pop()
                while sh is not None:
                    yield sh
                    try:
                        down = sh.GetDown()
                    except Exception:
                        down = None
                    if down is not None:
                        stack.append(down)
                    sh = sh.GetNext()

    def _write_path_refs(self, owner, raw: str, new_path: str) -> bool:
        targets = self._find_path_params(owner, raw)
        if not targets:
            seen: set = set()
            targets = []
            for holder in self._all_material_holders():
                if id(holder) in seen:
                    continue
                seen.add(id(holder))
                targets.extend(self._find_path_params(holder, raw))
        wrote = False
        done: set = set()
        for holder, paramid in targets:
            key = (id(holder), str(paramid))
            if key in done:
                continue
            done.add(key)
            try:
                self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, holder)
                holder[paramid] = new_path
                wrote = True
            except Exception:
                continue
        return wrote

    def _missing_texture_refs(self) -> list:
        import os
        doc = self.doc
        doc_path = doc.GetDocumentPath() or ""
        out: list = []
        seen: set = set()
        filled: list = []
        try:
            flags = getattr(c4d, "ASSETDATA_FLAG_TEXTURESONLY",
                            getattr(c4d, "ASSETDATA_FLAG_0", 0))
            c4d.documents.GetAllAssetsNew(doc, False, "", flags, filled)
        except Exception:
            filled = []
        for a in filled:
            if not isinstance(a, dict):
                continue
            raw = str(a.get("filename") or "")
            owner = a.get("owner")
            if not raw or owner is None or not self._is_texture_file(raw):
                continue
            try:
                resolved = c4d.GenerateTexturePath(doc_path, raw, "") or ""
            except Exception:
                resolved = ""
            if resolved and os.path.isfile(resolved):
                continue
            key = (id(owner), raw)
            if key in seen:
                continue
            seen.add(key)
            out.append((owner, raw))
        return out

    def relink_textures(self, folder: str, progress=None) -> dict:
        import os
        doc_path = self.doc.GetDocumentPath() or ""
        folder = (folder or "").strip().strip('"')
        if not folder or not os.path.isdir(folder):
            return {"relinked": 0, "not_found": 0, "skipped": 0,
                    "error": "Folder not found: %s" % (folder or "(empty)")}

        missing = self._missing_texture_refs()
        if not missing:
            return {"relinked": 0, "not_found": 0, "skipped": 0}

        index: dict = {}
        count = 0
        for root, _dirs, files in os.walk(folder):
            for fn in files:
                count += 1
                if progress and count % 200 == 0:
                    progress("Indexing search folder", 0, 0, root)
                index.setdefault(fn.lower(), os.path.join(root, fn))

        relinked = not_found = skipped = 0
        self.doc.StartUndo()
        for owner, raw in missing:
            found = index.get(os.path.basename(raw).lower())
            if found is None:
                not_found += 1
                continue
            new_path = found
            if doc_path:
                try:
                    rp = os.path.relpath(found, doc_path)
                    if not rp.startswith(".."):
                        new_path = rp.replace("\\", "/")
                except Exception:
                    pass
            if self._write_path_refs(owner, raw, new_path):
                relinked += 1
            else:
                skipped += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"relinked": relinked, "not_found": not_found,
                "skipped": skipped}

    def set_texture_path(self, raw: str, new_path: str,
                         material: str | None = None) -> dict:
        import os
        doc = self.doc
        doc_path = doc.GetDocumentPath() or ""
        filled: list = []
        try:
            flags = getattr(c4d, "ASSETDATA_FLAG_TEXTURESONLY",
                            getattr(c4d, "ASSETDATA_FLAG_0", 0))
            c4d.documents.GetAllAssetsNew(doc, False, "", flags, filled)
        except Exception:
            filled = []
        targets: list = []
        seen: set = set()
        for a in filled:
            if not isinstance(a, dict):
                continue
            owner = a.get("owner")
            if owner is None or str(a.get("filename") or "") != raw:
                continue
            if material and self._owner_material_name(owner) != material:
                continue
            if id(owner) in seen:
                continue
            seen.add(id(owner))
            targets.append(owner)
        if not targets:
            return {"changed": 0, "skipped": 0, "error": "reference not found"}

        write_path = new_path.strip()
        if write_path and doc_path and os.path.isabs(write_path):
            try:
                rp = os.path.relpath(write_path, doc_path)
                if not rp.startswith(".."):
                    write_path = rp.replace("\\", "/")
            except Exception:
                pass

        changed = skipped = 0
        doc.StartUndo()
        for owner in targets:
            if self._write_path_refs(owner, raw, write_path):
                changed += 1
            else:
                skipped += 1
        doc.EndUndo()
        c4d.EventAdd()
        return {"changed": changed, "skipped": skipped}

    def _owners_for_path(self, raw: str, material: str | None = None) -> list:
        filled: list = []
        try:
            flags = getattr(c4d, "ASSETDATA_FLAG_TEXTURESONLY",
                            getattr(c4d, "ASSETDATA_FLAG_0", 0))
            c4d.documents.GetAllAssetsNew(self.doc, False, "", flags, filled)
        except Exception:
            filled = []
        owners: list = []
        seen: set = set()
        for a in filled:
            if not isinstance(a, dict):
                continue
            owner = a.get("owner")
            if owner is None or str(a.get("filename") or "") != raw:
                continue
            if material and self._owner_material_name(owner) != material:
                continue
            if id(owner) in seen:
                continue
            seen.add(id(owner))
            owners.append(owner)
        return owners

    def _repath_targets(self, raws, mode: str) -> list:
        import os
        doc_path = self.doc.GetDocumentPath() or ""
        out: list = []
        seen: set = set()
        for raw in raws:
            if not raw or raw in seen:
                continue
            seen.add(raw)
            try:
                resolved = c4d.GenerateTexturePath(doc_path, raw, "") or ""
            except Exception:
                resolved = ""
            if not resolved or not os.path.isfile(resolved):
                continue
            if mode == "absolute":
                if os.path.isabs(raw):
                    continue
                out.append((raw, os.path.normpath(resolved)))
            else:
                if not os.path.isabs(raw) or not doc_path:
                    continue
                try:
                    rp = os.path.relpath(resolved, doc_path)
                except Exception:
                    continue
                if rp.startswith(".."):
                    continue
                out.append((raw, rp.replace("\\", "/")))
        return out

    def texture_repath(self, paths, mode: str = "relative",
                       material: str | None = None) -> dict:
        mode = "absolute" if str(mode).lower() == "absolute" else "relative"
        targets = self._repath_targets(list(paths or []), mode)
        self.last_changes = []
        if not targets:
            return {"changed": 0, "skipped": 0}

        changed = skipped = 0
        self.doc.StartUndo()
        for raw, new_path in targets:
            wrote = False
            for owner in self._owners_for_path(raw, material):
                if self._write_path_refs(owner, raw, new_path):
                    wrote = True
            if wrote:
                changed += 1
                self._log_texpath(raw, new_path)
            else:
                skipped += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"changed": changed, "skipped": skipped, "mode": mode}

    def texture_resize(self, paths, percent: int) -> dict:
        import os

        from ..core import textures as texmod
        try:
            percent = int(percent)
        except (TypeError, ValueError):
            percent = 0
        if percent not in texmod.RESIZE_PERCENTS:
            return {"resized": 0, "skipped": 0, "relinked": 0,
                    "error": "percent must be one of %s"
                    % (texmod.RESIZE_PERCENTS,)}
        has_pillow = False
        try:
            import PIL  # noqa: F401
            has_pillow = True
        except Exception:
            has_pillow = False

        doc_path = self.doc.GetDocumentPath() or ""
        results: list = []
        resized = skipped = relinked = 0
        done_copies: dict = {}
        self.last_changes = []
        seen_raw: set = set()

        self.doc.StartUndo()
        for raw in (paths or []):
            if not raw or raw in seen_raw:
                continue
            seen_raw.add(raw)
            base = os.path.basename(raw)
            try:
                resolved = c4d.GenerateTexturePath(doc_path, raw, "") or ""
            except Exception:
                resolved = ""
            ext = os.path.splitext(raw)[1].lower()
            ok, note = texmod.resize_decision(ext, has_pillow)
            if not resolved or not os.path.isfile(resolved):
                results.append({"file": base, "status": "skipped",
                                "note": "Datei fehlt"})
                skipped += 1
                continue
            if not ok:
                results.append({"file": base, "status": "skipped", "note": note})
                skipped += 1
                continue

            dst = texmod.resize_target(resolved, percent)
            wrote = done_copies.get(resolved)
            if wrote is None:
                wrote = texmod.resize_file(resolved, dst, percent, has_pillow)
                done_copies[resolved] = wrote
            if not wrote:
                results.append({"file": base, "status": "skipped",
                                "note": "Verkleinern fehlgeschlagen"})
                skipped += 1
                continue

            new_raw = texmod.resize_target(raw, percent)
            relinked_here = False
            for owner in self._owners_for_path(raw):
                if self._write_path_refs(owner, raw, new_raw):
                    relinked_here = True
            if relinked_here:
                relinked += 1
                self._log_texpath(raw, new_raw)
            resized += 1
            results.append({"file": base, "status": "resized",
                            "note": "", "to": os.path.basename(new_raw)})
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"resized": resized, "skipped": skipped, "relinked": relinked,
                "results": results}

    def _log_texpath(self, before: str, after: str) -> None:
        self.last_changes.append({
            "field": "texpath",
            "name": before,
            "before": before,
            "after": after,
        })

    def clear_missing_textures(self) -> dict:
        missing = self._missing_texture_refs()
        if not missing:
            return {"cleared": 0, "skipped": 0}
        cleared = skipped = 0
        self.doc.StartUndo()
        for owner, raw in missing:
            if self._write_path_refs(owner, raw, ""):
                cleared += 1
            else:
                skipped += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"cleared": cleared, "skipped": skipped}

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
            entry = {"name": name, "color": None,
                     "solo": False, "view": True, "render": True,
                     "locked": False,
                     "materials": mats.get(name, 0), "tags": tags.get(name, 0)}
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
            if lay.GetName() not in keep and self._is_layer_empty(lay.GetName(), obj_counts, mats, tags):
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
            if lay.GetName() == name and self._is_layer_empty(
                    name, obj_counts, mats, tags):
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

    def delete_unused_materials(self, include_hidden: bool = False) -> int:
        doc = self.doc
        used_any, used_visible = self._material_usage()
        protected = used_visible if include_hidden else used_any
        targets = [m for m in doc.GetMaterials()
                   if self._mat_key(m) not in protected]
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

    def _log_change(self, obj, field: str, before, after) -> None:
        self.last_changes.append({
            "sid": stable_id(obj),
            "name": obj.GetName(),
            "field": field,
            "before": before,
            "after": after,
        })

    def apply_renames(self, renames: list[RenameOp]) -> int:
        self.last_changes = []
        if not renames:
            return 0
        self.doc.StartUndo()
        count = 0
        for op in renames:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            before = obj.GetName()
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetName(op.new_name)
            self._log_change(obj, "name", before, op.new_name)
            count += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    def rename_object(self, guid: int, new_name: str) -> bool:
        obj = self._by_guid.get(guid)
        if obj is None:
            return False
        self.last_changes = []
        before = obj.GetName()
        if before == new_name:
            return True
        self.doc.StartUndo()
        self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
        obj.SetName(new_name)
        self._log_change(obj, "name", before, new_name)
        self.doc.EndUndo()
        c4d.EventAdd()
        return True

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

    def apply_layers(self, layerops: list[LayerOp]) -> int:
        self.last_changes = []
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
            before = self._current_layer_name(obj)
            layer = self._find_or_create_layer(op.layer, created, cache)
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetLayerObject(layer)
            self._log_change(obj, "layer", before, op.layer)
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
            self._log_change(obj, "parent", op.from_group, op.to_group)
            count += 1
        return count

    def apply_reparents(self, reparents: list[ReparentOp], canonical=None) -> int:
        self.last_changes = []
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
        self.last_changes = []
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
            before = obj.GetName()
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetName(op.new_name)
            self._log_change(obj, "name", before, op.new_name)
            renamed += 1
        reparented = self._do_reparents(reparents, created, canonical)
        layered = 0
        for op in layerops:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            before = self._current_layer_name(obj)
            layer = self._find_or_create_layer(op.layer, created, lay_cache)
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetLayerObject(layer)
            self._log_change(obj, "layer", before, op.layer)
            layered += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"renames": renamed, "reparents": reparented, "layers": layered}

    def _resolve_change(self, item: dict):
        obj = self._by_sid.get(item.get("sid"))
        if obj is not None:
            return obj
        wanted = item.get("after") if item.get("field") == "name" else item.get("name")
        for cand in self._by_guid.values():
            if cand.GetName() == wanted:
                return cand
        return None

    def revert(self, items: list[dict], canonical=None) -> dict:
        reverted = 0
        missing = 0
        results: list = []
        self.doc.StartUndo()
        created: list = []
        cache: dict = {}
        for item in items:
            field = item.get("field")
            note = {"name": item.get("name"), "field": field}

            if field == "texpath":
                before = item.get("before")
                after = item.get("after")
                wrote = False
                for owner in self._owners_for_path(after):
                    if self._write_path_refs(owner, after, before):
                        wrote = True
                if wrote:
                    reverted += 1
                    results.append({**note, "status": "reverted"})
                else:
                    missing += 1
                    results.append({**note, "status": "missing"})
                continue

            obj = self._resolve_change(item)
            if obj is None:
                missing += 1
                results.append({**note, "status": "missing"})
                continue
            before = item.get("before")

            if field == "name":
                self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                obj.SetName(before)
            elif field == "layer":
                self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                if before:
                    obj.SetLayerObject(
                        self._find_or_create_layer(before, created, cache))
                else:
                    obj.SetLayerObject(None)
            elif field == "parent":
                self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                mg = obj.GetMg()
                obj.Remove()
                if before and before not in ("(root)", "/"):
                    obj.InsertUnderLast(
                        self.ensure_group_path(before, created, canonical))
                else:
                    self.doc.InsertObject(obj)
                obj.SetMg(mg)
            else:
                results.append({**note, "status": "skipped"})
                continue
            reverted += 1
            results.append({**note, "status": "reverted"})

        self.doc.EndUndo()
        c4d.EventAdd()
        return {"reverted": reverted, "missing": missing, "results": results}

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


def _sidecar_path(doc) -> str | None:
    import os
    try:
        path = doc.GetDocumentPath() or ""
        name = doc.GetDocumentName() or ""
    except Exception:
        return None
    if not path or not name:
        return None
    return os.path.join(path, name + ".sohistory.json")


def _read_json_file(path: str) -> list:
    import json
    import os
    try:
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    return []


def _write_json_file(path: str, entries: list) -> None:
    import json
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _container_read(doc) -> list:
    import json
    try:
        bc = doc.GetDataInstance()
        raw = bc.GetString(DOC_JOURNAL_ID) if bc is not None else ""
        if raw:
            return json.loads(raw) or []
    except Exception:
        pass
    return []


def _container_write(doc, entries: list) -> None:
    import json
    try:
        bc = doc.GetDataInstance()
        if bc is not None:
            bc.SetString(DOC_JOURNAL_ID, json.dumps(entries, ensure_ascii=False))
            doc.SetChanged()
    except Exception:
        pass


def load_journal(doc, fallback_path: str) -> list:
    entries = journalmod.merge_journals(
        _container_read(doc), _read_json_file(_sidecar_path(doc) or ""))
    if not entries:
        entries = _read_json_file(fallback_path)
    return journalmod.normalize_journal(entries)


def save_journal(doc, entries: list, fallback_path: str) -> None:
    entries = journalmod.normalize_journal(entries)
    _container_write(doc, entries)
    side = _sidecar_path(doc)
    if side:
        _write_json_file(side, entries)
    else:
        _write_json_file(fallback_path, entries)
