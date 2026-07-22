from __future__ import annotations

import os

from ...core.textures.base import TextureResizeBase

_BLENDER_SAVE_FORMATS = {
    ".png": "PNG",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".tif": "TIFF",
    ".tiff": "TIFF",
    ".bmp": "BMP",
    ".tga": "TARGA",
    ".exr": "OPEN_EXR",
    ".hdr": "HDR",
}


class BlenderTextureResize(TextureResizeBase):

    def _image_has_alpha(self, path: str) -> bool:
        from ...core.textures import analysis as texmod
        try:
            info = texmod.analyze_image(path)
        except Exception:
            info = None
        return bool(info and info.has_alpha)

    def _host_resize(self, src: str, dst: str, percent: int) -> bool:
        from ...core.textures import analysis as texmod
        ext = os.path.splitext(dst)[1].lower()
        fmt = _BLENDER_SAVE_FORMATS.get(ext)
        if fmt is None:
            return False
        if self._image_has_alpha(src) and ext not in texmod.PURE_RESIZE_EXTS:
            return False

        bpy = self.bpy
        img = None
        try:
            img = bpy.data.images.load(src, check_existing=False)
            w, h = int(img.size[0]), int(img.size[1])
            if w <= 0 or h <= 0:
                return False
            nw, nh = texmod.scaled_dims(w, h, percent)
            img.scale(nw, nh)
            img.file_format = fmt
            img.filepath_raw = dst
            img.save()
            return os.path.isfile(dst)
        except Exception:
            return False
        finally:
            if img is not None:
                try:
                    bpy.data.images.remove(img)
                except Exception:
                    pass

    def _relink_resized(self, raw: str, new_raw: str) -> bool:
        wrote = False
        for img in self._match_images(raw):
            if self._set_image_path(img, new_raw):
                wrote = True
        return wrote

    def texture_resize(self, paths, percent) -> dict:
        from ... import vendor
        from ...core.textures import analysis as texmod
        try:
            percent = int(percent)
        except (TypeError, ValueError):
            percent = 0
        if percent not in texmod.RESIZE_PERCENTS:
            return {"resized": 0, "skipped": 0, "relinked": 0,
                    "error": "percent must be one of %s"
                    % (texmod.RESIZE_PERCENTS,)}

        has_pillow = vendor.import_pillow() is not None
        has_host = bool(_BLENDER_SAVE_FORMATS)
        results: list = []
        resized = skipped = relinked = 0
        done_copies: dict = {}
        seen_raw: set = set()
        self.last_changes = []

        for raw in (paths or []):
            if not raw or raw in seen_raw:
                continue
            seen_raw.add(raw)
            base = self._basename(raw)
            resolved = self._resolve(raw)
            ext = os.path.splitext(raw)[1].lower()
            ok, note = texmod.resize_decision(ext, has_pillow, has_host)
            if not resolved or not os.path.isfile(resolved):
                results.append({"file": base, "status": "skipped",
                                "note": "file is missing"})
                skipped += 1
                continue
            if not ok:
                results.append({"file": base, "status": "skipped", "note": note})
                skipped += 1
                continue
            if not has_pillow and self._image_has_alpha(resolved) \
                    and ext not in texmod.PURE_RESIZE_EXTS:
                results.append({"file": base, "status": "skipped",
                                "note": "has an alpha channel - the bundled "
                                        "resizer is missing"})
                skipped += 1
                continue

            dst = texmod.resize_target(resolved, percent)
            cache_key = os.path.normcase(resolved)
            wrote = done_copies.get(cache_key)
            if wrote is None:
                wrote = texmod.resize_file(resolved, dst, percent, has_pillow) \
                    or self._host_resize(resolved, dst, percent)
                done_copies[cache_key] = wrote
            if not wrote:
                note = "has an alpha channel - the bundled resizer is missing" \
                    if self._image_has_alpha(resolved) and not has_pillow \
                    else "could not write the resized copy"
                results.append({"file": base, "status": "skipped", "note": note})
                skipped += 1
                continue

            new_raw = texmod.resize_target(raw, percent)
            if self._relink_resized(raw, new_raw):
                relinked += 1
                self._log_texpath(raw, new_raw)
                resized += 1
                results.append({"file": base, "status": "resized",
                                "note": "", "to": self._basename(new_raw)})
            else:
                skipped += 1
                results.append({
                    "file": base, "status": "skipped",
                    "note": "copy written (%s), but the material could not be "
                            "relinked to it" % self._basename(new_raw)})
        if resized:
            self.doc.undo_push("Overseer: resize textures")
            self.doc.tag_redraw()
        return {"resized": resized, "skipped": skipped, "relinked": relinked,
                "results": results}
