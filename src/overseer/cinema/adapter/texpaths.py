from __future__ import annotations

import c4d


class TexturePathOps:

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

    def _iter_shader_tree(self, mat):
        """EVERY shader under the material, plugin types included."""
        try:
            first = mat.GetFirstShader()
        except Exception:
            return
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

    def _container_texture_paths(self, holder) -> list:
        """Texture-looking string values in the holder's raw BaseContainer.
        Plugin shaders (Octane's ImageTexture stores its file in container
        id 1100, Redshift & friends vary) do NOT publish their file params
        in the DESCRIPTION — GetDescription yields only the base-shader
        entries — so a description walk comes back empty and the container
        is the only reliable source. Matched by extension, not by id."""
        out: list = []
        try:
            bc = holder.GetDataInstance()
        except Exception:
            return out
        if bc is None:
            return out
        try:
            for _pid, val in bc:
                if isinstance(val, str) and val \
                        and self._is_texture_file(val):
                    out.append(val)
        except Exception:
            pass
        return out

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

    def _stored_path_for(self, owner, resolved: str) -> str:
        import os
        base = os.path.basename(resolved).lower()
        if not base or owner is None:
            return resolved
        holders = [owner]
        try:
            main = owner.GetMain()
            if main is not None and main is not owner:
                holders.append(main)
        except Exception:
            pass
        for holder in list(holders):
            try:
                holders.extend(self._iter_bitmap_shaders(holder))
            except Exception:
                pass
        for holder in holders:
            try:
                val = str(holder[c4d.BITMAPSHADER_FILENAME] or "")
            except Exception:
                val = ""
            if val and os.path.basename(val).lower() == base:
                return val
            try:
                description = holder.GetDescription(c4d.DESCFLAGS_DESC_NONE)
            except Exception:
                description = ()
            for _bc, paramid, _group in description:
                try:
                    v = holder[paramid]
                except Exception:
                    continue
                if isinstance(v, str) and v and \
                        os.path.basename(v).lower() == base:
                    return v
            # Plugin shaders keep file params out of the description —
            # the raw container is the only place the stored path shows.
            for v in self._container_texture_paths(holder):
                if os.path.basename(v).lower() == base:
                    return v
        return resolved

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
                resolved = str(a.get("filename") or "")
            except Exception:
                resolved = ""
            if not resolved or not self._is_texture_file(resolved):
                continue
            owner = a.get("owner")
            raw = self._stored_path_for(owner, resolved)
            name = self._owner_material_name(owner) \
                or str(a.get("assetname") or "")
            key = (name, raw)
            if key in seen:
                continue
            seen.add(key)
            used = name in used_names or name not in all_names
            refs.append((name, raw, used))
        # ALWAYS also walk the material shader trees and merge (dedupe by
        # material+path): GetAllAssetsNew does not report the textures of
        # every renderer — C4D 2026 + Octane returns none at all — and a
        # partial asset list must not hide the rest.
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
            holders = [m]
            holders.extend(self._iter_shader_tree(m))
            for holder in holders:
                for raw in self._container_texture_paths(holder):
                    key = (name, raw)
                    if key in seen:
                        continue
                    seen.add(key)
                    refs.append((name, raw, used))
        return refs

    def scan_textures(self, include_hidden: bool = True, accepted=None) -> dict:
        import os
        accepted_set = {str(p) for p in (accepted or [])}

        from ...core import imagesize
        from ...core import textures as texmod
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
                "vram": texmod.vram_bytes(
                    width, height,
                    channels=info.channels,
                    bit_depth=info.bit_depth) if info else 0,
                "accepted": raw in accepted_set,
            }
            entries.append(entry)
        absolute = [e for e in entries if e["absolute"]]
        relative = [e for e in entries if not e["absolute"]]
        total_bytes = sum(size for size, _ in meta_cache.values())
        total_vram = sum(texmod.vram_bytes(info.width, info.height,
                                           channels=info.channels,
                                           bit_depth=info.bit_depth)
                         for _size, info in meta_cache.values()
                         if info is not None)
        return {
            "doc_path": doc_path,
            "total": len(entries),
            "absolute_count": len(absolute),
            "relative_count": len(relative),
            "missing_count": sum(1 for e in entries
                                 if e["missing"] and not e["accepted"]),
            "relocatable_count": sum(1 for e in entries if e["relocatable"]),
            "total_bytes": total_bytes,
            "total_vram": total_vram,
            "absolute": absolute,
            "relative": relative,
            "accepted": sorted({e["path"] for e in entries
                                if e["missing"] and e["accepted"]}),
            "accepted_all": sorted(accepted_set),
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

    def _collect_candidates(self, only: set | None,
                            paths: list | None = None) -> tuple[list, list]:
        import os
        doc = self.doc
        doc_path = doc.GetDocumentPath() or ""
        refs: dict = {}
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
            owner = a.get("owner")
            resolved = str(a.get("filename") or "")
            if owner is None or not resolved \
                    or not self._is_texture_file(resolved):
                continue
            raw = self._stored_path_for(owner, resolved)
            entry = refs.setdefault(raw, (resolved, []))
            if not any(o is owner for o in entry[1]):
                entry[1].append(owner)

        try:
            mats = doc.GetMaterials()
        except Exception:
            mats = []
        for m in mats:
            for sh in self._iter_bitmap_shaders(m):
                try:
                    raw = str(sh[c4d.BITMAPSHADER_FILENAME] or "")
                except Exception:
                    continue
                if not raw:
                    continue
                try:
                    resolved = c4d.GenerateTexturePath(doc_path, raw, "") or raw
                except Exception:
                    resolved = raw
                entry = refs.setdefault(raw, (resolved, []))
                if not any(o is sh for o in entry[1]):
                    entry[1].append(sh)

        targets: list = []
        diag: list = []
        for raw, (resolved, owners) in refs.items():
            if only is not None and not any(
                    self._owner_material_name(o) in only for o in owners):
                continue
            if paths is not None and not any(
                    self._same_path(raw, p) or self._same_path(resolved, p)
                    for p in paths):
                continue
            if not os.path.isabs(raw):
                continue
            base = os.path.basename(raw) or raw
            if not os.path.isfile(resolved):
                diag.append("%s: the file cannot be found on disk" % base)
                continue
            try:
                rp = os.path.relpath(resolved, doc_path)
            except Exception:
                rp = ".."
            if not rp.startswith(".."):
                diag.append('%s: already inside the project'
                            ' (use "Make relative")' % base)
                continue
            targets.append((raw, resolved, owners))
        return targets, diag

    def texture_owners(self, path: str) -> dict:
        names: list = []
        if not (path or "").strip():
            return {"materials": names}
        try:
            mats = self.doc.GetMaterials()
        except Exception:
            mats = []
        for m in mats:
            held = False
            try:
                held = bool(self._find_path_params(m, path))
            except Exception:
                held = False
            if not held:
                try:
                    held = bool(self._node_path_ports(m, path))
                except Exception:
                    held = False
            if held:
                nm = m.GetName()
                if nm not in names:
                    names.append(nm)
        return {"materials": names}

    def collect_textures(self, materials: list | None = None,
                         subdir: str = "tex",
                         paths: list | None = None) -> dict:
        import filecmp
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
        raws = [str(p) for p in paths if p] if paths else None
        targets, diag = self._collect_candidates(only, raws)
        if not targets:
            return {"copied": 0, "relinked": 0, "skipped": 0,
                    "target": target_dir, "diag": diag}

        relinked = skipped = 0
        copies = [0]
        dest_by_src: dict = {}
        used_names: set = set()
        try:
            used_names = {fn.lower() for fn in os.listdir(target_dir)}
        except OSError:
            pass

        def same_file(a: str, b: str) -> bool:
            try:
                if os.path.getsize(a) != os.path.getsize(b):
                    return False
                return filecmp.cmp(a, b, shallow=False)
            except OSError:
                return False

        def dest_for(src: str) -> str | None:
            if src in dest_by_src:
                return dest_by_src[src]
            base = os.path.basename(src)
            dst = os.path.join(target_dir, base)
            try:
                if os.path.isfile(dst):
                    if same_file(dst, src):
                        dest_by_src[src] = dst
                        return dst
                    stem, ext = os.path.splitext(base)
                    n = 1
                    while True:
                        cname = "%s_%d%s" % (stem, n, ext)
                        cand = os.path.join(target_dir, cname)
                        if os.path.isfile(cand):
                            if same_file(cand, src):
                                dest_by_src[src] = cand
                                return cand
                        elif cname.lower() not in used_names:
                            dst = cand
                            break
                        n += 1
                shutil.copy2(src, dst)
                copies[0] += 1
                used_names.add(os.path.basename(dst).lower())
                dest_by_src[src] = dst
                return dst
            except OSError as ex:
                diag.append("cannot copy %s: %s" % (base, ex))
                return None

        doc.StartUndo()
        for raw, src, owners in targets:
            dst = dest_for(src)
            if dst is None:
                skipped += 1
                continue
            rel = subdir.replace("\\", "/") + "/" + os.path.basename(dst)
            wrote = False
            for owner in owners:
                if self._write_path_refs(owner, raw, rel):
                    wrote = True
            if self._write_path_anywhere(raw, rel):
                wrote = True
            if wrote:
                relinked += 1
            else:
                skipped += 1
                diag.append("%s: copied, but no parameter held the path"
                            % os.path.basename(src))
        doc.EndUndo()
        copied = copies[0]
        c4d.EventAdd()
        return {"copied": copied, "relinked": relinked, "skipped": skipped,
                "target": target_dir, "diag": diag}

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
                pass
            # Container ids invisible to the description (Octane & co) —
            # writable via plain int ids just the same.
            try:
                bc = holder.GetDataInstance()
                for pid, val in (bc or ()):
                    if isinstance(val, str) and self._same_path(val, raw):
                        out.append((holder, pid))
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

    _NODE_SPACE_IDS = (
        "com.redshift3d.redshift4c4d.class.nodespace",
        "net.maxon.nodespace.standard",
        "com.autodesk.arnold.nodespace",
        "com.chaos.vantage.class.nodespace",
    )

    def _node_space_ids(self) -> list:
        out: list = []
        try:
            import maxon
            for entry in maxon.registries.NodeSpaces:
                try:
                    sid = str(entry.GetId())
                except Exception:
                    continue
                if sid and sid not in out:
                    out.append(sid)
        except Exception:
            out = []
        for sid in self._NODE_SPACE_IDS:
            if sid not in out:
                out.append(sid)
        return out

    @staticmethod
    def _url_to_syspath(s: str) -> str:
        import os
        from urllib.parse import unquote
        s = str(s or "")
        if s.lower().startswith("file:///"):
            return unquote(s[len("file:///"):]).replace("/", os.sep)
        if s.lower().startswith("file://"):
            return unquote(s[len("file://"):]).replace("/", os.sep)
        return s

    @staticmethod
    def _syspath_to_url_string(p: str) -> str:
        import os
        p = (p or "").strip()
        if not p:
            return ""
        if "://" in p:
            return p
        q = p.replace("\\", "/")
        if os.path.isabs(p):
            return "file:///" + q.lstrip("/")
        return q

    def _node_path_ports(self, mat, raw: str) -> list:
        try:
            import maxon
        except ImportError:
            return []
        try:
            node_mat = mat.GetNodeMaterialReference()
        except Exception:
            return []
        if node_mat is None:
            return []
        out: list = []
        for sid in self._node_space_ids():
            try:
                spid = maxon.Id(sid)
                if not node_mat.HasSpace(spid):
                    continue
                graph = node_mat.GetGraph(spid)
                root = graph.GetViewRoot()
                nodes = list(root.GetInnerNodes(maxon.NODE_KIND.NODE, False))
            except Exception:
                continue
            for node in nodes:
                try:
                    stack = list(node.GetInputs().GetChildren())
                except Exception:
                    continue
                while stack:
                    port = stack.pop()
                    try:
                        stack.extend(port.GetChildren())
                    except Exception:
                        pass
                    try:
                        val = port.GetDefaultValue()
                    except Exception:
                        continue
                    is_url = isinstance(val, maxon.Url)
                    if is_url:
                        sval = self._url_to_syspath(str(val))
                    elif isinstance(val, str):
                        sval = val
                    else:
                        continue
                    if sval and self._same_path(sval, raw):
                        out.append((graph, port, is_url))
        return out

    def _node_path_values(self, limit: int = 6) -> list:
        out: list = []
        try:
            import maxon
        except ImportError:
            return out
        try:
            mats = list(self.doc.GetMaterials())
        except Exception:
            return out
        for mat in mats:
            try:
                node_mat = mat.GetNodeMaterialReference()
            except Exception:
                continue
            if node_mat is None:
                continue
            for sid in self._node_space_ids():
                try:
                    spid = maxon.Id(sid)
                    if not node_mat.HasSpace(spid):
                        continue
                    graph = node_mat.GetGraph(spid)
                    nodes = list(graph.GetViewRoot().GetInnerNodes(
                        maxon.NODE_KIND.NODE, False))
                except Exception:
                    continue
                for node in nodes:
                    try:
                        stack = list(node.GetInputs().GetChildren())
                    except Exception:
                        continue
                    while stack:
                        port = stack.pop()
                        try:
                            stack.extend(port.GetChildren())
                        except Exception:
                            pass
                        try:
                            val = port.GetDefaultValue()
                        except Exception:
                            continue
                        sval = str(val) if val is not None else ""
                        if not sval or len(sval) < 4:
                            continue
                        low = sval.lower()
                        if not any(low.endswith(e) for e in
                                   (".tif", ".tiff", ".png", ".jpg", ".jpeg",
                                    ".exr", ".tga", ".hdr", ".psd")):
                            continue
                        entry = "%s [%s]" % (sval, type(val).__name__)
                        if entry not in out:
                            out.append(entry)
                        if len(out) >= limit:
                            return out
        return out

    def _write_node_paths(self, mat, raw: str, new_path: str) -> bool:
        ports = self._node_path_ports(mat, raw)
        if not ports:
            return False
        import maxon
        try:
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, mat)
        except Exception:
            pass
        wrote = False
        by_graph: dict = {}
        for graph, port, is_url in ports:
            by_graph.setdefault(id(graph), (graph, []))[1].append((port, is_url))
        for graph, plist in by_graph.values():
            try:
                with graph.BeginTransaction() as tr:
                    for port, is_url in plist:
                        try:
                            if is_url:
                                port.SetDefaultValue(
                                    maxon.Url(self._syspath_to_url_string(new_path)))
                            else:
                                port.SetDefaultValue(new_path)
                            wrote = True
                        except Exception:
                            continue
                    tr.Commit()
            except Exception:
                continue
        return wrote

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
        try:
            if isinstance(owner, c4d.BaseMaterial) and \
                    self._write_node_paths(owner, raw, new_path):
                wrote = True
        except Exception:
            pass
        if not wrote:
            try:
                for m in self.doc.GetMaterials():
                    if self._write_node_paths(m, raw, new_path):
                        wrote = True
            except Exception:
                pass
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

    def _owner_index(self) -> dict:
        filled: list = []
        try:
            flags = getattr(c4d, "ASSETDATA_FLAG_TEXTURESONLY",
                            getattr(c4d, "ASSETDATA_FLAG_0", 0))
            c4d.documents.GetAllAssetsNew(self.doc, False, "", flags, filled)
        except Exception:
            filled = []
        index: dict = {}
        seen: set = set()
        for a in filled:
            if not isinstance(a, dict):
                continue
            owner = a.get("owner")
            resolved = str(a.get("filename") or "")
            if owner is None or not resolved:
                continue
            stored = self._stored_path_for(owner, resolved)
            for raw in {stored, resolved}:
                key = (raw, id(owner))
                if key in seen:
                    continue
                seen.add(key)
                index.setdefault(raw, []).append(owner)
        return index

    def _owners_for_path(self, raw: str, material: str | None = None,
                         index: dict | None = None) -> list:
        owners = (self._owner_index() if index is None
                  else index).get(raw, [])
        if not material:
            return list(owners)
        return [o for o in owners
                if self._owner_material_name(o) == material]

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

    def _write_path_anywhere(self, raw: str, new_path: str) -> bool:
        wrote = False
        seen: set = set()
        for holder in self._all_material_holders():
            if id(holder) in seen:
                continue
            seen.add(id(holder))
            for h, pid in self._find_path_params(holder, raw):
                try:
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, h)
                    h[pid] = new_path
                    wrote = True
                except Exception:
                    continue
        try:
            for m in self.doc.GetMaterials():
                if self._write_node_paths(m, raw, new_path):
                    wrote = True
        except Exception:
            pass
        return wrote

    def texture_repath(self, paths, mode: str = "relative",
                       material: str | None = None) -> dict:
        mode = "absolute" if str(mode).lower() == "absolute" else "relative"
        import os
        raws = [str(p) for p in (paths or []) if p]
        targets = self._repath_targets(raws, mode)
        self.last_changes = []
        if not targets:
            return {"changed": 0, "skipped": len(raws), "mode": mode,
                    "targets": 0,
                    "diag": [self._repath_diag(r, mode) for r in raws]}

        changed = skipped = 0
        diag: list = []
        index = self._owner_index()
        self.doc.StartUndo()
        for raw, new_path in targets:
            owners = self._owners_for_path(raw, material, index)
            wrote = False
            for owner in owners:
                if self._write_path_refs(owner, raw, new_path):
                    wrote = True
            if not wrote and not material:
                wrote = self._write_path_anywhere(raw, new_path)
            if wrote:
                changed += 1
                self._log_texpath(raw, new_path)
            else:
                skipped += 1
                diag.append("%s: %d owner(s), no parameter held the path"
                            % (os.path.basename(raw), len(owners)))

        if changed == 0 and skipped:
            seen_vals = self._node_path_values()
            if seen_vals:
                diag.append("graph holds: " + " | ".join(seen_vals))
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"changed": changed, "skipped": skipped, "mode": mode,
                "targets": len(targets), "diag": diag}

    def _repath_diag(self, raw: str, mode: str) -> str:
        import os
        doc_path = self.doc.GetDocumentPath() or ""
        base = os.path.basename(raw) or raw
        if not doc_path:
            return "%s: the project has never been saved" % base
        try:
            resolved = c4d.GenerateTexturePath(doc_path, raw, "") or ""
        except Exception:
            resolved = ""
        if not resolved or not os.path.isfile(resolved):
            return "%s: the file cannot be found on disk" % base
        if mode == "relative":
            if not os.path.isabs(raw):
                return "%s: already relative" % base
            try:
                rp = os.path.relpath(resolved, doc_path)
            except Exception:
                return "%s: not on the same drive as the project" % base
            if rp.startswith(".."):
                return "%s: lives outside the project folder" % base
        elif os.path.isabs(raw):
            return "%s: already absolute" % base
        return "%s: no change needed" % base

    def _log_texpath(self, before: str, after: str) -> None:
        self.last_changes.append({
            "field": "texpath",
            "name": before,
            "before": before,
            "after": after,
        })

    def clear_missing_textures(self, accepted=None) -> dict:
        accepted_set = {str(p) for p in (accepted or [])}
        missing = self._missing_texture_refs()
        if not missing:
            return {"cleared": 0, "skipped": 0}
        cleared = skipped = 0
        self.doc.StartUndo()
        for owner, raw in missing:
            if raw in accepted_set \
                    or self._stored_path_for(owner, raw) in accepted_set:
                continue
            if self._write_path_refs(owner, raw, ""):
                cleared += 1
            else:
                skipped += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"cleared": cleared, "skipped": skipped}
