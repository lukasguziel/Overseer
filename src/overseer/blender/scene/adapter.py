"""``SceneAdapter`` - the BScene <-> ``core.model.SceneTree`` bridge and the
composition root for every Blender scene mutation.

The Blender twin of ``cinema/scene/adapter.py``. Domain mutations live in the
mixins (materials / previews / texture paths / texture resize / collections /
apply), composed here exactly like the C4D adapter composes its mixins. This
base owns tree building, selection and focus.
"""
from __future__ import annotations

from ...core.hostapi import SceneAdapter as SceneAdapterPort
from ...core.scene import model
from ..layers import LayerOps
from ..materials import MaterialOps
from ..organize.apply import ApplyOps
from ..textures.paths import TexturePathOps
from ..textures.previews import PreviewOps
from ..textures.resize import TextureResizeOps
from .readers import (
    classify,
    editor_hidden,
    layer_name,
    own_geo,
    stable_id,
    type_name,
)


class SceneAdapter(MaterialOps, PreviewOps, TexturePathOps,
                   TextureResizeOps, LayerOps, ApplyOps,
                   SceneAdapterPort):

    def __init__(self, doc) -> None:
        self.doc = doc                      # a BScene
        self._by_guid: dict[int, object] = {}
        self._by_sid: dict[int, object] = {}
        self._selected_direct: set = set()
        self._selected_subtree: set = set()
        self.last_changes: list[dict] = []

    # -- helpers ------------------------------------------------------------
    @property
    def bpy(self):
        return self.doc._bpy

    def _master_collection(self):
        try:
            return self.doc.scene.collection
        except Exception:
            return None

    def _depsgraph(self):
        try:
            return self.bpy.context.evaluated_depsgraph_get()
        except Exception:
            return None

    # -- tree ---------------------------------------------------------------
    def build_tree(self, progress=None) -> model.SceneTree:
        self._by_guid.clear()
        self._by_sid.clear()
        self._selected_direct.clear()
        self._selected_subtree.clear()
        tree = model.SceneTree()
        counter = [0]

        objs = self.doc.objects()
        total = len(objs) if progress else 0
        master = self._master_collection()
        depsgraph = self._depsgraph()

        # Precompute object order + a parent->children adjacency map ONCE.
        # Both ``obj.children`` and ``list(scene.objects).index()`` are O(N) in
        # Blender (they scan every object), so using them per node made
        # build_tree O(N^2) and froze large scenes. Keyed on ``obj.name``
        # (file-global unique, a stable dict key — unlike ephemeral wrappers).
        present_names = {o.name for o in objs}
        order = {o.name: i for i, o in enumerate(objs)}
        children_map: dict = {}
        for o in objs:
            p = o.parent
            if p is not None and p.name in present_names:
                children_map.setdefault(p.name, []).append(o)
        for lst in children_map.values():
            lst.sort(key=lambda c: order.get(c.name, 0))

        def selected(obj) -> bool:
            return self.doc.object_selected(obj)

        def make(obj, parent, depth, sel_ancestor, hidden_ancestor):
            guid = counter[0]
            counter[0] += 1
            if progress and counter[0] % 50 == 0:
                progress(counter[0], total, getattr(obj, "name", ""))
            pts, polys = own_geo(obj, depsgraph)
            hidden = editor_hidden(obj, hidden_ancestor)
            node = model.SceneNode(
                name=obj.name,
                type_name=type_name(obj),
                category=classify(obj),
                guid=guid,
                depth=depth,
                point_count=pts,
                poly_count=polys,
                visible=not hidden,
                layer=layer_name(obj, master),
            )
            self._by_guid[guid] = obj
            self._by_sid[stable_id(obj)] = obj
            is_sel = selected(obj)
            in_scope = sel_ancestor or is_sel
            if is_sel:
                self._selected_direct.add(guid)
            if in_scope:
                self._selected_subtree.add(guid)
            # Pre-sorted adjacency (built once above) — no per-node O(N) scan.
            for child in children_map.get(obj.name, []):
                node.add_child(
                    make(child, node, depth + 1, in_scope, hidden))
            return node

        for root in self.doc.roots():
            tree.roots.append(make(root, None, 0, False, False))
        return tree

    def selected_guids(self, include_children: bool = True) -> set:
        return set(self._selected_subtree if include_children
                   else self._selected_direct)

    # -- host binding (SceneAdapter port) -----------------------------------
    def set_host(self, host) -> None:
        self.doc = host

    def refresh_selection(self, tree) -> None:
        self._selected_direct.clear()
        self._selected_subtree.clear()

        def visit(node, sel_ancestor):
            obj = self._by_guid.get(node.guid)
            is_sel = obj is not None and self.doc.object_selected(obj)
            if is_sel:
                self._selected_direct.add(node.guid)
            in_scope = sel_ancestor or is_sel
            if in_scope:
                self._selected_subtree.add(node.guid)
            for child in node.children:
                visit(child, in_scope)

        for root in tree.roots:
            visit(root, False)

    # -- focus --------------------------------------------------------------
    def focus(self, guid: int) -> bool:
        obj = self._by_guid.get(guid)
        if obj is None:
            return False
        try:
            for o in self.doc.selected_objects():
                o.select_set(False)
        except Exception:
            pass
        try:
            obj.select_set(True)
            self.bpy.context.view_layer.objects.active = obj
        except Exception:
            return False
        self._view_selected()
        self.doc.tag_redraw()
        return True

    def _view_selected(self) -> None:
        """Frame the active selection in the first 3D viewport (needs a
        temp context override pointing at that area/region)."""
        bpy = self.bpy
        try:
            win = bpy.context.window
            screen = bpy.context.screen
            for area in screen.areas:
                if area.type != "VIEW_3D":
                    continue
                region = next((r for r in area.regions
                               if r.type == "WINDOW"), None)
                if region is None:
                    continue
                with bpy.context.temp_override(window=win, area=area,
                                               region=region):
                    bpy.ops.view3d.view_selected()
                return
        except Exception:
            pass
