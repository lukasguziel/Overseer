from __future__ import annotations

import base64
import os


class PreviewOps:

    def material_previews(self, names=None, size=48, progress=None) -> dict:
        out: dict = {}
        by_name: dict = {}
        try:
            for m in self.bpy.data.materials:
                try:
                    by_name[m.name_full] = m
                except Exception:
                    continue
        except Exception:
            by_name = {}

        req = list(names) if names else list(by_name.keys())
        total = len(req)
        for i, name in enumerate(req):
            if progress:
                try:
                    progress(i, total, name)
                except Exception:
                    pass
            mat = by_name.get(name)
            uri = self._material_uri(mat, size) if mat is not None else None
            if uri is not None:
                out[name] = uri
        return out

    def texture_previews(self, paths=None, size=40, progress=None) -> dict:
        out: dict = {}
        all_paths = list(paths or [])
        total = len(all_paths)
        img_by_path = None
        for i, p in enumerate(all_paths):
            if progress:
                try:
                    progress(i, total, os.path.basename(str(p or "")))
                except Exception:
                    pass
            uri = None
            try:
                if p and os.path.isfile(p):
                    uri = self._pillow_uri(p, size)
                    if uri is None:
                        if img_by_path is None:
                            img_by_path = self._build_image_index()
                        img = img_by_path.get(self._norm_path(p))
                        if img is not None:
                            uri = self._image_preview_uri(img, size)
            except Exception:
                uri = None
            if uri is not None:
                out[p] = uri
        return out

    def _material_uri(self, mat, size: int):
        try:
            mat.preview_ensure()
        except Exception:
            pass
        try:
            prev = mat.preview
            if prev is None:
                return None
            w, h = prev.image_size
            if w <= 0 or h <= 0:
                return None
            flat = list(prev.image_pixels_float)
            if not flat or len(flat) < w * h * 4:
                return None
            raw = self._sample_rgba(flat, w, h, size, size)
            if not any(raw):
                return None
            return self._encode_uri(raw, size, size)
        except Exception:
            return None

    def _image_preview_uri(self, img, size: int):
        try:
            img.preview_ensure()
            prev = img.preview
            if prev is None:
                return None
            w, h = prev.image_size
            if w <= 0 or h <= 0:
                return None
            flat = list(prev.image_pixels_float)
            if not flat or len(flat) < w * h * 4:
                return None
            raw = self._sample_rgba(flat, w, h, size, size)
            if not any(raw):
                return None
            return self._encode_uri(raw, size, size)
        except Exception:
            return None

    def _pillow_uri(self, path: str, size: int):
        try:
            from ... import vendor
            image_mod = vendor.import_pillow()
        except Exception:
            image_mod = None
        if image_mod is None:
            return None
        try:
            import io
            with image_mod.open(path) as im:
                im = im.convert("RGBA")
                im = im.resize((size, size))
                buf = io.BytesIO()
                im.save(buf, format="PNG")
            data = base64.b64encode(buf.getvalue()).decode("ascii")
            return "data:image/png;base64," + data
        except Exception:
            return None

    def _norm_path(self, path: str):
        try:
            return os.path.normcase(os.path.abspath(path))
        except Exception:
            return None

    def _build_image_index(self) -> dict:
        index: dict = {}
        try:
            images = list(self.bpy.data.images)
        except Exception:
            return index
        for img in images:
            try:
                lib = getattr(img, "library", None)
                fp = self.bpy.path.abspath(img.filepath, library=lib)
            except Exception:
                fp = ""
            if not fp:
                continue
            key = self._norm_path(fp)
            if key is not None:
                index.setdefault(key, img)
        return index

    def _sample_rgba(self, flat, sw: int, sh: int, dw: int, dh: int) -> bytes:
        out = bytearray(dw * dh * 4)
        for dy in range(dh):
            sy = sh - 1 - (dy * sh // dh)
            base = sy * sw
            drow = dy * dw * 4
            for dx in range(dw):
                sx = dx * sw // dw
                si = (base + sx) * 4
                di = drow + dx * 4
                for k in range(4):
                    v = flat[si + k]
                    iv = int(v * 255.0 + 0.5)
                    out[di + k] = 0 if iv < 0 else (255 if iv > 255 else iv)
        return bytes(out)

    def _encode_uri(self, raw: bytes, w: int, h: int) -> str:
        png = self._png_bytes(w, h, raw)
        return "data:image/png;base64," + base64.b64encode(png).decode("ascii")

    def _png_bytes(self, width: int, height: int, raw: bytes) -> bytes:
        import struct
        import zlib

        def chunk(tag: bytes, data: bytes) -> bytes:
            body = tag + data
            return (struct.pack(">I", len(data)) + body
                    + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        stride = width * 4
        rows = bytearray()
        for y in range(height):
            rows.append(0)
            rows.extend(raw[y * stride:(y + 1) * stride])
        idat = zlib.compress(bytes(rows), 9)
        return (sig + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", idat) + chunk(b"IEND", b""))
