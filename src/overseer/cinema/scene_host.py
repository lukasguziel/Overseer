"""CDoc - the SceneHost port over a live Cinema 4D ``BaseDocument``.

The C4D twin of ``blender.scene.BScene``. Wraps the raw c4d document so the
shared op layer treats it identically to the Blender host; the c4d adapter still
works on the raw document (exposed as ``.raw``).
"""
from __future__ import annotations

import c4d

from ..core.hostapi import SceneHost


class CDoc(SceneHost):

    def __init__(self, doc) -> None:
        self.raw = doc

    @classmethod
    def active(cls) -> CDoc | None:
        doc = c4d.documents.GetActiveDocument()
        return cls(doc) if doc is not None else None

    # -- identity -----------------------------------------------------------
    @property
    def name(self) -> str:
        return self.raw.GetDocumentName() or ""

    @property
    def path(self) -> str:
        return self.raw.GetDocumentPath() or ""

    # c4d-parity aliases (some ported helpers call these names)
    def GetDocumentName(self) -> str:  # noqa: N802 - c4d parity
        return self.name

    def GetDocumentPath(self) -> str:  # noqa: N802 - c4d parity
        return self.path

    # -- dirty token --------------------------------------------------------
    def dirty(self) -> int:
        try:
            return int(self.raw.GetDirty(
                c4d.DIRTYFLAGS_OBJECT | c4d.DIRTYFLAGS_DATA))
        except Exception:
            return 0

    def GetDirty(self, *args) -> int:  # noqa: N802 - c4d parity
        return self.dirty()

    # -- selection ----------------------------------------------------------
    def selection_token(self) -> tuple:
        try:
            objs = self.raw.GetActiveObjects(
                c4d.GETACTIVEOBJECTFLAGS_SELECTIONORDER)
        except Exception:
            try:
                objs = self.raw.GetActiveObjects(0)
            except Exception:
                objs = []
        objs = objs or []
        names: list = []
        token = len(objs)
        for o in objs:
            try:
                nm = o.GetName()
                token = (token * 131 + hash((nm, o.GetType()))) & 0xFFFFFFFF
            except Exception:
                nm = ""
            if len(names) < 6:
                names.append(nm)
        return token, names, len(objs)

    # -- hierarchy (SceneHost completeness; the c4d adapter uses .raw) -------
    def objects(self) -> list:
        out: list = []
        stack: list = []
        op = self.raw.GetFirstObject()
        while op or stack:
            if op is None:
                op = stack.pop()
            out.append(op)
            down = op.GetDown()
            nxt = op.GetNext()
            if down and nxt:
                stack.append(nxt)
            op = down or nxt
        return out

    def roots(self) -> list:
        out: list = []
        op = self.raw.GetFirstObject()
        while op:
            out.append(op)
            op = op.GetNext()
        return out

    # -- mutation plumbing --------------------------------------------------
    def undo_push(self, message: str = "Overseer") -> None:
        # C4D adapters wrap their own StartUndo/AddUndo/EndUndo per op, so there
        # is no separate push here.
        return None

    def tag_redraw(self) -> None:
        try:
            c4d.EventAdd()
        except Exception:
            pass

    def status(self, text: str | None) -> None:
        try:
            if text:
                c4d.StatusSetText(str(text))
            else:
                c4d.StatusClear()
        except Exception:
            pass
