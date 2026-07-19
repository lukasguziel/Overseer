"""TexturePathOps - texture scan + path rewriting for Blender.

STUB: implemented by a dedicated subagent. Reference: cinema/adapter/texpaths.py.
Textures are ``bpy.data.images`` + Image Texture nodes; ``//`` prefix = blend-
relative. Use ``bpy.path.abspath``/``relpath``. Mirror the C4D return-dict
shapes exactly (scan_textures, make_textures_relative, texture_owners,
collect_textures, relink_textures, clear_missing_textures, set_texture_path,
texture_repath).
"""
from __future__ import annotations


class TexturePathOps:

    def scan_textures(self, include_hidden=False, accepted=None) -> dict:
        return {"textures": [], "missing": [], "summary": {}}

    def make_textures_relative(self, materials=None) -> dict:
        return {"fixed": 0}

    def texture_owners(self, path: str) -> dict:
        return {"materials": [], "objects": []}

    def collect_textures(self, materials=None, subdir="tex", paths=None) -> dict:
        return {"copied": 0, "relinked": 0}

    def relink_textures(self, folder: str, progress=None) -> dict:
        return {"relinked": 0, "checked": 0}

    def clear_missing_textures(self, accepted=None) -> dict:
        return {"cleared": 0}

    def set_texture_path(self, path: str, new_path: str, material=None) -> dict:
        return {"changed": 0}

    def texture_repath(self, paths, mode="relative", material=None) -> dict:
        return {"changed": 0}
