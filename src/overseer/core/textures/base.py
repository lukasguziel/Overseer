from __future__ import annotations

import os
from abc import abstractmethod

from ..items import ItemsBase


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
        from . import analysis as texmod
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
                    info = texmod.analyze_image(resolved)
                    meta_cache[resolved] = (disk_bytes, info)
            entries.append(texmod.texture_row(
                material, used, raw, resolved, absolute, exists, relocatable,
                rel_target, disk_bytes, info, raw in accepted_set))
        return texmod.texture_scan_result(entries, doc_path, accepted_set,
                                          meta_cache.values())

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
