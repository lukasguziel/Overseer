"""PreviewOps - material + texture thumbnails as data-URIs for Blender.

STUB: implemented by a dedicated subagent. Reference: cinema/adapter/previews.py.
Prefer Blender's ``preview`` images / Pillow from ``vendor/``; a transparent
1x1 PNG data-URI is an acceptable fallback. Return ``dict[key, dataURI]``.
"""
from __future__ import annotations

# 1x1 transparent PNG - safe fallback so the UI always gets a valid data-URI.
_BLANK = ("data:image/png;base64,"
          "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
          "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


class PreviewOps:

    def material_previews(self, names, size=48, progress=None) -> dict:
        return {name: _BLANK for name in (names or [])}

    def texture_previews(self, paths, size=40, progress=None) -> dict:
        return {}
