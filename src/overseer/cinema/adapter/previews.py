from __future__ import annotations

import c4d


class PreviewOps:

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
