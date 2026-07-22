from __future__ import annotations

from abc import abstractmethod

from ..hostapi.items import ItemsBase


class TexturePathsBase(ItemsBase):
    """Texture references: scan, relink, repath, collect. The shared workflow
    lives here; a host overrides only the primitives that read or write its
    own shader/image system."""

    @abstractmethod
    def scan_textures(self, include_hidden=False, accepted=None) -> dict: ...

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
