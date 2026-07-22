from __future__ import annotations

import os

from ...core.textures.base import TexturePathsBase


class BlenderTexturePaths(TexturePathsBase):

    @staticmethod
    def _norm(path: str) -> str:
        return os.path.normcase(os.path.normpath((path or "").strip()))

    @staticmethod
    def _basename(path: str) -> str:
        return str(path or "").replace("\\", "/").rsplit("/", 1)[-1]

    def _mat_name(self, mat) -> str:
        try:
            return getattr(mat, "name_full", None) or mat.name
        except Exception:
            return ""

    def _img_key(self, img) -> str:
        try:
            return getattr(img, "name_full", None) or img.name
        except Exception:
            return "id:%d" % id(img)

    def _raw(self, img) -> str:
        for attr in ("filepath_raw", "filepath"):
            try:
                val = getattr(img, attr)
            except Exception:
                val = ""
            if val:
                return str(val)
        return ""

    def _resolve(self, raw: str, library=None) -> str:
        if not raw:
            return ""
        try:
            resolved = self.bpy.path.abspath(raw, library=library)
        except Exception:
            try:
                resolved = self.bpy.path.abspath(raw)
            except Exception:
                resolved = raw
        try:
            return os.path.normpath(resolved)
        except Exception:
            return resolved

    def _library_for_raw(self, raw: str):
        try:
            for img in self._real_images():
                try:
                    if self._raw(img) == raw:
                        return getattr(img, "library", None)
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _real_images(self) -> list:
        try:
            images = list(self.bpy.data.images)
        except Exception:
            return []
        out: list = []
        for img in images:
            try:
                if getattr(img, "source", "") in ("GENERATED", "VIEWER", "TILED"):
                    continue
                if getattr(img, "packed_file", None) is not None:
                    continue
                raw = self._raw(img)
            except Exception:
                continue
            if not raw:
                continue
            out.append(img)
        return out

    def _images_in_node_tree(self, node_tree, seen: set) -> list:
        if node_tree is None:
            return []
        try:
            nodes = list(node_tree.nodes)
        except Exception:
            return []
        out: list = []
        for node in nodes:
            try:
                img = getattr(node, "image", None)
                if img is not None:
                    out.append(img)
                sub = getattr(node, "node_tree", None)
                if sub is not None:
                    key = getattr(sub, "name_full", None) or id(sub)
                    if key not in seen:
                        seen.add(key)
                        out.extend(self._images_in_node_tree(sub, seen))
            except Exception:
                continue
        return out

    def _image_material_map(self) -> dict:
        out: dict = {}
        try:
            mats = list(self.bpy.data.materials)
        except Exception:
            mats = []
        for mat in mats:
            try:
                name = self._mat_name(mat)
                if not name:
                    continue
                tree = getattr(mat, "node_tree", None)
                for img in self._images_in_node_tree(tree, set()):
                    out.setdefault(self._img_key(img), set()).add(name)
            except Exception:
                continue
        return out

    def _all_material_names(self) -> set:
        try:
            return {self._mat_name(m) for m in self.bpy.data.materials}
        except Exception:
            return set()

    def _material_usage(self) -> tuple[set, set]:
        used_any: set = set()
        used_visible: set = set()
        try:
            objs = self.doc.objects()
        except Exception:
            objs = []
        for obj in objs:
            try:
                visible = bool(obj.visible_get())
            except Exception:
                visible = True
            try:
                slots = list(obj.material_slots)
            except Exception:
                slots = []
            for slot in slots:
                try:
                    mat = slot.material
                except Exception:
                    mat = None
                if mat is None:
                    continue
                name = self._mat_name(mat)
                used_any.add(name)
                if visible:
                    used_visible.add(name)
        return used_any, used_visible

    def _match_images(self, path: str, material: str | None = None) -> list:
        if not (path or "").strip():
            return []
        target_norm = self._norm(path)
        target_abs = self._norm(self._resolve(path))
        mats_for = self._image_material_map() if material else None
        out: list = []
        for img in self._real_images():
            try:
                raw = self._raw(img)
                lib = getattr(img, "library", None)
                if self._norm(raw) == target_norm or (
                        target_abs and self._norm(self._resolve(raw, lib)) == target_abs):
                    if material and material not in mats_for.get(self._img_key(img), set()):
                        continue
                    out.append(img)
            except Exception:
                continue
        return out

    def _to_blend_relative(self, abspath: str, doc_path: str) -> str | None:
        if not abspath or not doc_path:
            return None
        rel = None
        try:
            candidate = self.bpy.path.relpath(abspath, start=doc_path)
        except Exception:
            candidate = None
        if candidate and candidate.startswith("//"):
            rel = candidate
        if rel is None:
            try:
                rp = os.path.relpath(abspath, doc_path)
            except Exception:
                return None
            if rp.startswith(".."):
                return None
            rel = "//" + rp.replace("\\", "/")
        tail = rel[2:].replace("\\", "/")
        if tail.startswith("../") or tail == ".." or "/../" in tail:
            return None
        return rel

    def _set_image_path(self, img, path: str, reload: bool = True) -> bool:
        if not reload:
            try:
                img.filepath_raw = path
            except Exception:
                return False
            return True

        try:
            img.filepath = path
        except Exception:
            return False
        try:
            img.filepath_raw = path
        except Exception:
            pass
        if path:
            try:
                img.reload()
            except Exception:
                pass
        lib = getattr(img, "library", None)
        if lib is not None:
            try:
                lib.reload()
            except Exception:
                pass
        return True

    def _log_texpath(self, before: str, after: str) -> None:
        self.last_changes.append({
            "field": "texpath",
            "name": before,
            "before": before,
            "after": after,
        })

    def _doc_path(self) -> str:
        return self.doc.path or ""

    def _normalize_ref(self, img, raw: str, material: str, used: bool):
        doc_path = self.doc.path or ""
        resolved = self._resolve(raw, getattr(img, "library", None))
        blend_relative = raw.startswith("//")
        absolute = (not blend_relative) and os.path.isabs(raw)
        exists = bool(resolved) and os.path.isfile(resolved)
        relocatable = False
        rel_target = ""
        if absolute and exists and doc_path:
            rel = self._to_blend_relative(resolved, doc_path)
            if rel is not None:
                relocatable = True
                rel_target = rel[2:] if rel.startswith("//") else rel
        return (raw, resolved, material, used, absolute, relocatable,
                rel_target)

    def get_texture_refs(self, include_hidden: bool = True):
        used_any, used_visible = self._material_usage()
        used_names = used_any if include_hidden else used_visible
        all_names = self._all_material_names()
        image_to_mats = self._image_material_map()

        for img in self._real_images():
            try:
                raw = self._raw(img)
                if not raw:
                    continue
                mats = sorted(image_to_mats.get(self._img_key(img), set()))
                if not mats:
                    try:
                        orphan_used = bool(getattr(img, "users", 0))
                    except Exception:
                        orphan_used = False
                    yield self._normalize_ref(img, raw, "", orphan_used)
                    continue
                for name in mats:
                    used = name in used_names or name not in all_names
                    yield self._normalize_ref(img, raw, name, used)
            except Exception:
                continue

    def make_textures_relative(self, materials: list | None = None) -> dict:
        doc_path = self.doc.path or ""
        if not doc_path:
            return {"fixed": 0,
                    "error": "Project is not saved (no folder to make paths relative to)."}
        only = set(materials) if materials else None
        image_to_mats = self._image_material_map() if only is not None else None

        fixed = 0
        for img in self._real_images():
            try:
                raw = self._raw(img)
                if not raw or raw.startswith("//") or not os.path.isabs(raw):
                    continue
                if only is not None and not (
                        image_to_mats.get(self._img_key(img), set()) & only):
                    continue
                resolved = self._resolve(raw, getattr(img, "library", None))
                if not os.path.isfile(resolved):
                    continue
                rel = self._to_blend_relative(resolved, doc_path)
                if rel is None:
                    continue
                if self._set_image_path(img, rel, reload=False):
                    fixed += 1
            except Exception:
                continue
        if fixed:
            self.doc.undo_push("Overseer: make textures relative")
            self.doc.tag_redraw()
        return {"fixed": fixed}

    def texture_owners(self, path: str) -> dict:
        if not (path or "").strip():
            return {"materials": [], "objects": []}
        imgs = self._match_images(path)
        img_keys = {self._img_key(i) for i in imgs}
        image_to_mats = self._image_material_map()
        mat_names: set = set()
        for key in img_keys:
            mat_names |= image_to_mats.get(key, set())

        objects: list = []
        try:
            objs = self.doc.objects()
        except Exception:
            objs = []
        for obj in objs:
            try:
                slots = list(obj.material_slots)
            except Exception:
                slots = []
            for slot in slots:
                try:
                    mat = slot.material
                except Exception:
                    mat = None
                if mat is not None and self._mat_name(mat) in mat_names:
                    objects.append(obj.name)
                    break
        return {"materials": sorted(mat_names),
                "objects": sorted(set(objects))}

    def collect_textures(self, materials: list | None = None,
                         subdir: str = "tex",
                         paths: list | None = None) -> dict:
        import filecmp
        import shutil
        doc_path = self.doc.path or ""
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
        image_to_mats = self._image_material_map()

        candidates: list = []
        diag: list = []
        for img in self._real_images():
            try:
                raw = self._raw(img)
                if not raw or raw.startswith("//") or not os.path.isabs(raw):
                    continue
                if only is not None and not (
                        image_to_mats.get(self._img_key(img), set()) & only):
                    continue
                resolved = self._resolve(raw, getattr(img, "library", None))
                if raws is not None and not any(
                        self._norm(raw) == self._norm(p)
                        or self._norm(resolved) == self._norm(self._resolve(p))
                        for p in raws):
                    continue
                base = self._basename(raw) or raw
                if not os.path.isfile(resolved):
                    diag.append("%s: the file cannot be found on disk" % base)
                    continue
                if self._to_blend_relative(resolved, doc_path) is not None:
                    diag.append('%s: already inside the project'
                                ' (use "Make relative")' % base)
                    continue
                candidates.append((raw, resolved, img))
            except Exception:
                continue
        if not candidates:
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

        def dest_for(src: str):
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

        for _raw, src, img in candidates:
            try:
                dst = dest_for(src)
                if dst is None:
                    skipped += 1
                    continue
                rel = "//" + subdir.replace("\\", "/") + "/" + os.path.basename(dst)
                if self._set_image_path(img, rel, reload=False):
                    relinked += 1
                else:
                    skipped += 1
                    diag.append("%s: copied, but the image could not be relinked"
                                % os.path.basename(src))
            except Exception:
                skipped += 1
                continue
        copied = copies[0]
        if relinked or copied:
            self.doc.undo_push("Overseer: collect textures")
            self.doc.tag_redraw()
        return {"copied": copied, "relinked": relinked, "skipped": skipped,
                "target": target_dir, "diag": diag}

    def relink_textures(self, folder: str, progress=None) -> dict:
        doc_path = self.doc.path or ""
        folder = (folder or "").strip().strip('"')
        if not folder or not os.path.isdir(folder):
            return {"relinked": 0, "not_found": 0, "skipped": 0,
                    "error": "Folder not found: %s" % (folder or "(empty)")}

        missing: list = []
        for img in self._real_images():
            try:
                raw = self._raw(img)
                if not raw:
                    continue
                resolved = self._resolve(raw, getattr(img, "library", None))
                if not resolved or not os.path.isfile(resolved):
                    missing.append((img, raw))
            except Exception:
                continue
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
        for img, raw in missing:
            try:
                found = index.get(self._basename(raw).lower())
                if found is None:
                    not_found += 1
                    continue
                new_path = found
                if doc_path:
                    rel = self._to_blend_relative(found, doc_path)
                    if rel is not None:
                        new_path = rel
                if self._set_image_path(img, new_path):
                    relinked += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
                continue
        if relinked:
            self.doc.undo_push("Overseer: relink textures")
            self.doc.tag_redraw()
        return {"relinked": relinked, "not_found": not_found,
                "skipped": skipped}

    def clear_missing_textures(self, accepted=None) -> dict:
        accepted_set = {str(p) for p in (accepted or [])}
        missing: list = []
        for img in self._real_images():
            try:
                raw = self._raw(img)
                if not raw:
                    continue
                resolved = self._resolve(raw, getattr(img, "library", None))
                if not resolved or not os.path.isfile(resolved):
                    missing.append((img, raw))
            except Exception:
                continue
        if not missing:
            return {"cleared": 0, "skipped": 0}

        cleared = skipped = 0
        for img, raw in missing:
            try:
                if raw in accepted_set \
                        or self._resolve(raw, getattr(img, "library", None)) in accepted_set:
                    continue
                if self._set_image_path(img, "", reload=False):
                    cleared += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
                continue
        if cleared:
            self.doc.undo_push("Overseer: clear missing textures")
            self.doc.tag_redraw()
        return {"cleared": cleared, "skipped": skipped}

    def set_texture_path(self, path: str, new_path: str,
                         material: str | None = None) -> dict:
        doc_path = self.doc.path or ""
        imgs = self._match_images(path, material)
        if not imgs:
            return {"changed": 0, "skipped": 0, "error": "reference not found"}

        write_path = (new_path or "").strip()
        if write_path and doc_path and not write_path.startswith("//") \
                and os.path.isabs(write_path):
            rel = self._to_blend_relative(os.path.normpath(write_path), doc_path)
            if rel is not None:
                write_path = rel

        changed = skipped = 0
        for img in imgs:
            try:
                if self._set_image_path(img, write_path):
                    changed += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
                continue
        if changed:
            self.doc.undo_push("Overseer: set texture path")
            self.doc.tag_redraw()
        return {"changed": changed, "skipped": skipped}

    def _repath_targets(self, raws, mode: str) -> list:
        doc_path = self.doc.path or ""
        out: list = []
        seen: set = set()
        for raw in raws:
            if not raw or raw in seen:
                continue
            seen.add(raw)
            resolved = self._resolve(raw, self._library_for_raw(raw))
            if not resolved or not os.path.isfile(resolved):
                continue
            blend_rel = raw.startswith("//")
            if mode == "absolute":
                if os.path.isabs(raw) and not blend_rel:
                    continue
                out.append((raw, os.path.normpath(resolved)))
            else:
                if blend_rel or not os.path.isabs(raw) or not doc_path:
                    continue
                rel = self._to_blend_relative(os.path.normpath(resolved), doc_path)
                if rel is None:
                    continue
                out.append((raw, rel))
        return out

    def texture_repath(self, paths, mode: str = "relative",
                       material: str | None = None) -> dict:
        mode = "absolute" if str(mode).lower() == "absolute" else "relative"
        raws = [str(p) for p in (paths or []) if p]
        self.last_changes = []
        targets = self._repath_targets(raws, mode)
        if not targets:
            return {"changed": 0, "skipped": len(raws), "mode": mode,
                    "targets": 0,
                    "diag": [self._repath_diag(r, mode) for r in raws]}

        changed = skipped = 0
        diag: list = []
        for raw, new_path in targets:
            imgs = self._match_images(raw, material)
            wrote = False
            for img in imgs:
                try:
                    if self._set_image_path(img, new_path):
                        wrote = True
                except Exception:
                    continue
            if wrote:
                changed += 1
                self._log_texpath(raw, new_path)
            else:
                skipped += 1
                diag.append("%s: no image held the path"
                            % self._basename(raw))
        if changed:
            self.doc.undo_push("Overseer: repath textures")
            self.doc.tag_redraw()
        return {"changed": changed, "skipped": skipped, "mode": mode,
                "targets": len(targets), "diag": diag}

    def _repath_diag(self, raw: str, mode: str) -> str:
        doc_path = self.doc.path or ""
        base = self._basename(raw) or raw
        if not doc_path:
            return "%s: the project has never been saved" % base
        resolved = self._resolve(raw, self._library_for_raw(raw))
        if not resolved or not os.path.isfile(resolved):
            return "%s: the file cannot be found on disk" % base
        blend_rel = raw.startswith("//")
        if mode == "relative":
            if blend_rel or not os.path.isabs(raw):
                return "%s: already relative" % base
            if self._to_blend_relative(os.path.normpath(resolved), doc_path) is None:
                return "%s: lives outside the project folder" % base
        elif os.path.isabs(raw) and not blend_rel:
            return "%s: already absolute" % base
        return "%s: no change needed" % base
