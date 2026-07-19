"""``BScene`` - the Blender analog of a C4D ``doc``.

``blender/webapi.py`` threads a ``BScene`` through every handler the way
``cinema/webapi.py`` threads a live ``c4d`` document. It exposes only the
handful of document-level operations the handlers need (name/path, a stable
dirty token, selection, undo push, the object set) mapped onto ``bpy``.

This is the ONLY place (besides the adapter and audits) that reads
document-level ``bpy`` state, so the rest of the webapi stays host-neutral.
"""
from __future__ import annotations

import os

from ..core.hostapi import SceneHost


class BScene(SceneHost):
    """Thin wrapper over the active Blender scene + ``bpy.data``.

    Implements the ``SceneHost`` port (the normalized "document"), so the shared
    op layer treats it identically to the C4D document wrapper."""

    def __init__(self, bpy_module, scene) -> None:
        self._bpy = bpy_module
        self.scene = scene

    # -- construction -------------------------------------------------------
    @classmethod
    def active(cls) -> BScene | None:
        try:
            import bpy
        except Exception:
            return None
        scene = getattr(bpy.context, "scene", None)
        if scene is None:
            return None
        return cls(bpy, scene)

    # -- identity -----------------------------------------------------------
    @property
    def filepath(self) -> str:
        return self._bpy.data.filepath or ""

    @property
    def name(self) -> str:
        fp = self.filepath
        return os.path.basename(fp) if fp else "(unsaved)"

    @property
    def path(self) -> str:
        fp = self.filepath
        return os.path.dirname(fp) if fp else ""

    # C4D-compatible aliases so ported helpers can call the same names.
    def GetDocumentName(self) -> str:  # noqa: N802 - c4d parity
        return self.name

    def GetDocumentPath(self) -> str:  # noqa: N802 - c4d parity
        return self.path

    # -- dirty token --------------------------------------------------------
    def dirty(self) -> int:
        """An O(1) edit token that bumps on any data edit (transform, geometry,
        rename, add/remove) but NOT on selection or camera moves.

        Backed by the singleton ``host`` edit-epoch counter, which a
        depsgraph_update_post handler advances (mirrors C4D's native O(1)
        ``doc.GetDirty()``). Was an O(N) per-object per-character hash that the
        function audit flagged as a main-thread stall on large scenes. The
        cross-request scene cache is keyed on this so guids stay stable between
        a plan and its apply; mutating ops also call ``invalidate_scene_cache``.
        """
        try:
            from . import host
            return int(host.edit_epoch())
        except Exception:
            return 0

    # C4D parity: DIRTYFLAGS args are ignored, we return the fingerprint.
    def GetDirty(self, *args) -> int:  # noqa: N802 - c4d parity
        return self.dirty()

    # -- selection ----------------------------------------------------------
    def selected_objects(self) -> list:
        try:
            return list(self._bpy.context.selected_objects)
        except Exception:
            return []

    def selection_token(self) -> tuple:
        """Return ``(token, names, count)`` like ``_selection_info`` in the
        C4D webapi: a hash of the current selection plus up to 6 names."""
        objs = self.selected_objects()
        names: list = []
        token = len(objs)
        for o in objs:
            try:
                nm = o.name
                token = (token * 131 + hash((nm, o.type))) & 0xFFFFFFFF
            except Exception:
                nm = ""
            if len(names) < 6:
                names.append(nm)
        return token, names, len(objs)

    # -- hierarchy ----------------------------------------------------------
    def objects(self) -> list:
        """All objects in the active scene (any collection depth)."""
        try:
            return list(self.scene.objects)
        except Exception:
            return []

    def roots(self) -> list:
        """Top-level objects: parent is None or parent is outside this scene,
        in a stable order (scene object order)."""
        try:
            present = set(self.scene.objects)
        except Exception:
            return []
        out = []
        for o in self.scene.objects:
            p = o.parent
            if p is None or p not in present:
                out.append(o)
        return out

    # -- mutation plumbing --------------------------------------------------
    def undo_push(self, message: str = "Overseer") -> None:
        try:
            self._bpy.ops.ed.undo_push(message=message)
        except Exception:
            pass

    def tag_redraw(self) -> None:
        """Best-effort viewport/UI refresh after a mutation."""
        try:
            self._bpy.context.view_layer.update()
        except Exception:
            pass
        try:
            for area in self._bpy.context.screen.areas:
                area.tag_redraw()
        except Exception:
            pass

    def status(self, text: str | None) -> None:
        try:
            ws = self._bpy.context.workspace
            ws.status_text_set(text)
        except Exception:
            pass
