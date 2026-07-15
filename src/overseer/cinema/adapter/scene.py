from __future__ import annotations

import c4d

from ...core import model
from .apply import ApplyOps
from .layers import LayerOps
from .materials import MaterialOps
from .previews import PreviewOps
from .readers import classify, editor_hidden, layer_name, own_geo, stable_id, type_name
from .texpaths import TexturePathOps
from .texresize import TextureResizeOps


class SceneAdapter(MaterialOps, PreviewOps, TexturePathOps,
                   TextureResizeOps, LayerOps, ApplyOps):

    def __init__(self, doc) -> None:
        self.doc = doc
        self._by_guid: dict[int, object] = {}
        self._by_sid: dict[int, object] = {}
        self._selected_direct: set = set()
        self._selected_subtree: set = set()
        self.last_changes: list[dict] = []

    def count_objects(self) -> int:
        n = 0
        stack = []
        op = self.doc.GetFirstObject()
        while op or stack:
            if op is None:
                op = stack.pop()
            n += 1
            down = op.GetDown()
            nxt = op.GetNext()
            if down and nxt:
                stack.append(nxt)
            op = down or nxt
        return n

    def build_tree(self, progress=None) -> model.SceneTree:
        self._by_guid.clear()
        self._by_sid.clear()
        self._selected_direct.clear()
        self._selected_subtree.clear()
        tree = model.SceneTree()
        counter = [0]
        total = self.count_objects() if progress else 0

        def make(op, parent, depth, sel_ancestor, hidden_ancestor):
            guid = counter[0]
            counter[0] += 1
            if progress and counter[0] % 50 == 0:
                progress(counter[0], total, op.GetName())
            pts, polys = own_geo(op)
            hidden = editor_hidden(op, hidden_ancestor)
            node = model.SceneNode(
                name=op.GetName(),
                type_name=type_name(op),
                category=classify(op),
                guid=guid,
                depth=depth,
                point_count=pts,
                poly_count=polys,
                visible=not hidden,
                layer=layer_name(op),
            )
            self._by_guid[guid] = op
            self._by_sid[stable_id(op)] = op
            is_sel = bool(op.GetBit(c4d.BIT_ACTIVE))
            in_scope = sel_ancestor or is_sel
            if is_sel:
                self._selected_direct.add(guid)
            if in_scope:
                self._selected_subtree.add(guid)
            child = op.GetDown()
            while child:
                node.add_child(make(child, node, depth + 1, in_scope, hidden))
                child = child.GetNext()
            return node

        top = self.doc.GetFirstObject()
        while top:
            tree.roots.append(make(top, None, 0, False, False))
            top = top.GetNext()
        return tree

    def selected_guids(self, include_children: bool = True) -> set:
        return set(self._selected_subtree if include_children
                   else self._selected_direct)

    def focus(self, guid: int) -> bool:
        op = self._by_guid.get(guid)
        if op is None:
            return False
        self.doc.SetActiveObject(op, c4d.SELECTION_NEW)

        up = op.GetUp()
        while up is not None:
            up.SetBit(c4d.BIT_OFOLD)
            up = up.GetUp()
        try:
            c4d.CallCommand(100004769)
        except Exception:
            pass

        bd = self.doc.GetActiveBaseDraw()
        cam = None
        if bd is not None:
            cam = bd.GetSceneCamera(self.doc) or bd.GetEditorCamera()
        if cam is not None:
            mg = op.GetMg()
            center = mg * op.GetMp()
            rad = op.GetRad()
            sx, sy, sz = mg.v1.GetLength(), mg.v2.GetLength(), mg.v3.GetLength()
            r = max(rad.x * sx, rad.y * sy, rad.z * sz)
            if r <= 0:
                r = 100.0
            cm = cam.GetMg()
            forward = cm.v3
            dist = r * 2.8
            cm.off = center - forward * dist
            self.doc.StartUndo()
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, cam)
            cam.SetMg(cm)
            self.doc.EndUndo()

        c4d.EventAdd()
        try:
            c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
        except Exception:
            pass
        return True
