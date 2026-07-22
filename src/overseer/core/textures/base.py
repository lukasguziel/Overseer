from __future__ import annotations

import os
from abc import abstractmethod

from ..items import ItemsBase
from . import imagesize
from .analysis import analyze_image, vram_bytes


class TexturePathsBase(ItemsBase):
    """Texture references: scan, relink, repath, collect. The shared workflow
    lives here; a host overrides only the primitives that read or write its
    own shader/image system."""

    @abstractmethod
    def _doc_path(self) -> str:
        """Directory of the saved document ("" if unsaved)."""

    @abstractmethod
    def get_texture_refs(self, include_hidden=True):
        """Yield one normalized tuple per texture reference:
        ``(raw, resolved, material, used, absolute, relocatable,
        rel_target)``. Every host read (shaders / images / node graphs)
        happens here; the base turns the tuples into the canonical rows."""

    def scan_textures(self, include_hidden=True, accepted=None) -> dict:
        accepted_set = {str(p) for p in (accepted or [])}
        doc_path = self._doc_path()
        entries: list = []
        meta_cache: dict = {}
        for (raw, resolved, material, used, absolute,
             relocatable, rel_target) in self.get_texture_refs(include_hidden):
            exists = bool(resolved) and os.path.isfile(resolved)
            disk_bytes = 0
            info = None
            if exists:
                if resolved in meta_cache:
                    disk_bytes, info = meta_cache[resolved]
                else:
                    try:
                        disk_bytes = os.path.getsize(resolved)
                    except Exception:
                        disk_bytes = 0
                    info = analyze_image(resolved)
                    meta_cache[resolved] = (disk_bytes, info)
            entries.append(self.texture_row(
                material, used, raw, resolved, absolute, exists, relocatable,
                rel_target, disk_bytes, info, raw in accepted_set))
        return self.texture_scan_result(entries, doc_path, accepted_set,
                                        meta_cache.values())

    @staticmethod
    def texture_row(material: str, used: bool, raw: str, resolved: str,
                    absolute: bool, exists: bool, relocatable: bool,
                    rel_target: str, disk_bytes: int, info,
                    accepted: bool) -> dict:
        width = info.width if info else 0
        height = info.height if info else 0
        res_tag = imagesize.resolution_tag(max(width, height)) if info else ""
        return {
            "material": material,
            "used": used,
            "file": str(raw or "").replace("\\", "/").rsplit("/", 1)[-1],
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
            "vram": vram_bytes(width, height,
                               channels=info.channels,
                               bit_depth=info.bit_depth) if info else 0,
            "accepted": accepted,
        }

    @staticmethod
    def texture_scan_result(entries: list, doc_path: str, accepted_set,
                            metas) -> dict:
        accepted_set = set(accepted_set or ())
        metas = list(metas)
        absolute = [e for e in entries if e["absolute"]]
        relative = [e for e in entries if not e["absolute"]]
        total_bytes = sum(size for size, _ in metas)
        total_vram = sum(vram_bytes(info.width, info.height,
                                    channels=info.channels,
                                    bit_depth=info.bit_depth)
                         for _size, info in metas if info is not None)
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

    @abstractmethod
    def make_textures_relative(self, materials=None) -> dict: ...

    @abstractmethod
    def texture_owners(self, path: str) -> dict: ...

    @abstractmethod
    def collect_textures(self, materials=None, subdir="tex", paths=None) -> dict: ...

    @abstractmethod
    def relink_textures(self, folder: str, progress=None) -> dict: ...

    @abstractmethod
    def clear_missing_textures(self, accepted=None) -> dict: ...

    @abstractmethod
    def set_texture_path(self, path: str, new_path: str, material=None) -> dict: ...

    @abstractmethod
    def texture_repath(self, paths, mode="relative", material=None) -> dict: ...


class TextureResizeBase(ItemsBase):
    """Resized texture copies + relink."""

    @abstractmethod
    def texture_resize(self, paths, percent) -> dict: ...


class PreviewsBase(ItemsBase):
    """Material/texture preview thumbnails as data URIs."""

    @abstractmethod
    def material_previews(self, names, size=48, progress=None) -> dict: ...

    @abstractmethod
    def texture_previews(self, paths, size=40, progress=None) -> dict: ...
