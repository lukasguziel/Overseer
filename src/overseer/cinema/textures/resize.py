from __future__ import annotations

import c4d

from ...core.textures.base import TextureResizeBase
from ..scene.readers import _SAVE_FILTERS


class CinemaTextureResize(TextureResizeBase):

    def _has_alpha(self, path: str) -> bool:
        try:
            bmp = c4d.bitmaps.BaseBitmap()
            if bmp.InitWith(path)[0] != c4d.IMAGERESULT_OK:
                return False
            return bmp.GetInternalChannelCount() > 0
        except Exception:
            return False

    def _host_resize(self, src: str, dst: str, percent: int) -> bool:
        import os

        from ...core.textures import analysis as texmod
        try:
            bmp = c4d.bitmaps.BaseBitmap()
            if bmp.InitWith(src)[0] != c4d.IMAGERESULT_OK:
                return False
            try:
                if bmp.GetInternalChannelCount() > 0:
                    return False
            except Exception:
                pass
            w, h = bmp.GetSize()
            nw, nh = texmod.scaled_dims(w, h, percent)
            small = c4d.bitmaps.BaseBitmap()
            if small.Init(nw, nh, bmp.GetBt()) != c4d.IMAGERESULT_OK:
                return False
            scaled = False
            try:
                bmp.ScaleBicubic(small, 0, 0, w - 1, h - 1, 0, 0, nw - 1, nh - 1)
                scaled = True
            except Exception:
                scaled = False
            if not scaled:
                bmp.ScaleIt(small, 256, True, False)
            fmt = _SAVE_FILTERS.get(os.path.splitext(dst)[1].lower())
            if fmt is None:
                return False
            save_bits = c4d.SAVEBIT_0
            if bmp.GetBt() not in (8, 24):
                save_bits |= getattr(c4d, "SAVEBIT_32BITCHANNELS", 0)
            return small.Save(dst, fmt, None,
                              save_bits) == c4d.IMAGERESULT_OK
        except Exception:
            return False

    def texture_resize(self, paths, percent: int) -> dict:
        import os

        from ...core.textures import analysis as texmod
        try:
            percent = int(percent)
        except (TypeError, ValueError):
            percent = 0
        if percent not in texmod.RESIZE_PERCENTS:
            return {"resized": 0, "skipped": 0, "relinked": 0,
                    "error": "percent must be one of %s"
                    % (texmod.RESIZE_PERCENTS,)}
        from ... import vendor
        has_pillow = vendor.import_pillow() is not None
        has_host = bool(_SAVE_FILTERS)

        doc_path = self.doc.GetDocumentPath() or ""
        results: list = []
        resized = skipped = relinked = 0
        done_copies: dict = {}
        self.last_changes = []
        seen_raw: set = set()
        index = self._owner_index()

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

            dst = texmod.resize_target(resolved, percent)
            wrote = done_copies.get(resolved)
            if wrote is None:
                wrote = texmod.resize_file(resolved, dst, percent, has_pillow) \
                    or self._host_resize(resolved, dst, percent)
                done_copies[resolved] = wrote
            if not wrote:
                note = "has an alpha channel — the bundled resizer is missing" \
                    if self._has_alpha(resolved) and not has_pillow \
                    else "could not write the resized copy"
                results.append({"file": base, "status": "skipped",
                                "note": note})
                skipped += 1
                continue

            new_raw = texmod.resize_target(raw, percent)
            relinked_here = False
            for owner in self._owners_for_path(raw, None, index):
                if self._write_path_refs(owner, raw, new_raw):
                    relinked_here = True
            if not relinked_here:
                relinked_here = self._write_path_anywhere(raw, new_raw)
            if relinked_here:
                relinked += 1
                self._log_texpath(raw, new_raw)
                resized += 1
                results.append({"file": base, "status": "resized",
                                "note": "", "to": os.path.basename(new_raw)})
            else:
                skipped += 1
                results.append({
                    "file": base, "status": "skipped",
                    "note": "copy written (%s), but the material could not be "
                            "relinked to it" % os.path.basename(new_raw)})
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"resized": resized, "skipped": skipped, "relinked": relinked,
                "results": results}
