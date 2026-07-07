"""C4D adapter: builds a pure SceneTree from a document and writes
operations (rename/reparent) back with undo support.

This is the ONLY domain module that imports `c4d`. It is never loaded
by the unit tests.
"""

from __future__ import annotations

import collections

import c4d

from . import model
from .ops import LayerOp, RenameOp, ReparentOp

# Colors for the automatically created type layers (RGB 0..1).
LAYER_COLORS = {
    "Lights": (0.98, 0.75, 0.14),
    "Cameras": (0.22, 0.74, 0.97),
    "Proxies": (0.69, 0.48, 1.0),
    "Splines": (0.55, 0.60, 0.70),
}

KNOWN_TYPES = {
    c4d.Onull: "Null",
    c4d.Ocamera: "Camera",
    c4d.Olight: "Light",
    c4d.Opolygon: "Mesh",
    c4d.Ospline: "Spline",
    c4d.Oinstance: "Instance",
    1018544: "MoGraph Cloner",
    1018545: "MoGraph Matrix",
    1018791: "MoGraph Fracture",
    1019268: "MoGraph Text",
}

RS_LIGHT_IDS = {1036751}
RS_CAMERA_IDS = {1057516}


def type_name(op) -> str:
    t = op.GetType()
    if t in KNOWN_TYPES:
        return KNOWN_TYPES[t]
    try:
        n = op.GetTypeName()
        if n:
            return n
    except Exception:
        pass
    return "type_%d" % t


def _virtual_geo(op) -> tuple:
    """(points, polygons) across a cache subtree (virtual objects).

    Traverses the geometry produced by the generator (deform/cache tree) via
    GetDown/GetNext. Only counts counter ints, NEVER iterates over individual
    polygons -> fast even with millions of polys.
    """
    pts = polys = 0
    o = op
    while o:
        if o.IsInstanceOf(c4d.Opolygon):
            try:
                pts += o.GetPointCount()
                polys += o.GetPolygonCount()
            except Exception:
                pass
        dc = o.GetDeformCache()
        if dc:
            p2, q2 = _virtual_geo(dc)
            pts += p2
            polys += q2
        c = o.GetCache()
        if c:
            p2, q2 = _virtual_geo(c)
            pts += p2
            polys += q2
        down = o.GetDown()
        if down:
            p2, q2 = _virtual_geo(down)
            pts += p2
            polys += q2
        o = o.GetNext()
    return pts, polys


def own_geo(op) -> tuple:
    """(points, polygons) of ONE scene object (without scene-graph children).

    Editable poly object -> direct counters. Generator (Cube, Cloner, Sweep
    ...) -> geometry from its cache. This way primitives/MoGraph also get a
    realistic poly count instead of 0.
    """
    if op.IsInstanceOf(c4d.Opolygon):
        try:
            return op.GetPointCount(), op.GetPolygonCount()
        except Exception:
            return 0, 0
    cache = op.GetDeformCache() or op.GetCache()
    if cache is None:
        return 0, 0
    return _virtual_geo(cache)


def classify(op) -> str:
    t = op.GetType()
    if op.CheckType(c4d.Ocamera) or t in RS_CAMERA_IDS:
        return model.CAT_CAMERA
    if op.CheckType(c4d.Olight) or t in RS_LIGHT_IDS:
        return model.CAT_LIGHT
    tn = type_name(op).lower()
    if "light" in tn or "licht" in tn:
        return model.CAT_LIGHT
    if "camera" in tn or "kamera" in tn:
        return model.CAT_CAMERA
    if op.CheckType(c4d.Onull):
        return model.CAT_NULL
    if op.CheckType(c4d.Ospline):
        return model.CAT_SPLINE
    if op.CheckType(c4d.Opolygon):
        return model.CAT_MESH
    return model.CAT_OTHER


class SceneAdapter:
    """Bidirectional bridge document <-> SceneTree."""

    def __init__(self, doc) -> None:
        self.doc = doc
        self._by_guid: dict[int, object] = {}
        # Selection is captured during tree construction (BIT_ACTIVE is
        # stable per object). GetActiveObjects/id(op) does NOT work: C4D
        # returns new Python wrappers on every API call -> id() never matches.
        self._selected_direct: set = set()
        self._selected_subtree: set = set()

    # -- Reading ----------------------------------------------------------
    def count_objects(self) -> int:
        """Fast object count (names/geometry untouched) for progress totals."""
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
        """Builds the SceneTree. `progress(current, total, detail)` is called
        every few objects so long scans can drive a preloader."""
        self._by_guid.clear()
        self._selected_direct.clear()
        self._selected_subtree.clear()
        tree = model.SceneTree()
        counter = [0]
        total = self.count_objects() if progress else 0

        def make(op, parent, depth, sel_ancestor):
            guid = counter[0]
            counter[0] += 1
            if progress and counter[0] % 50 == 0:
                progress(counter[0], total, op.GetName())
            pts, polys = own_geo(op)
            node = model.SceneNode(
                name=op.GetName(),
                type_name=type_name(op),
                category=classify(op),
                guid=guid,
                depth=depth,
                point_count=pts,
                poly_count=polys,
            )
            self._by_guid[guid] = op
            is_sel = bool(op.GetBit(c4d.BIT_ACTIVE))
            in_scope = sel_ancestor or is_sel
            if is_sel:
                self._selected_direct.add(guid)
            if in_scope:
                self._selected_subtree.add(guid)
            child = op.GetDown()
            while child:
                node.add_child(make(child, node, depth + 1, in_scope))
                child = child.GetNext()
            return node

        top = self.doc.GetFirstObject()
        while top:
            tree.roots.append(make(top, None, 0, False))
            top = top.GetNext()
        return tree

    def selected_guids(self, include_children: bool = True) -> set:
        """guids of the currently selected objects (optionally incl. children).

        Must be called after build_tree() -- the selection is captured there
        via the BIT_ACTIVE flag.
        """
        return set(self._selected_subtree if include_children
                   else self._selected_direct)

    def focus(self, guid: int) -> bool:
        """Select the object exclusively and frame the camera on it (like 'S').

        Sets the active camera directly onto the object's bounding box -- this
        works regardless of which viewport currently has focus
        (CallCommand(Frame) would be a no-op if the web panel has focus).
        Main thread, after build_tree().
        """
        op = self._by_guid.get(guid)
        if op is None:
            return False
        self.doc.SetActiveObject(op, c4d.SELECTION_NEW)

        # Unfold the ancestor chain so the highlighted object is actually
        # visible in the Object Manager (BIT_OFOLD = expanded in the OM).
        up = op.GetUp()
        while up is not None:
            up.SetBit(c4d.BIT_OFOLD)
            up = up.GetUp()
        try:
            # Object Manager: "Scroll To First Active" (best effort; the
            # command id is stable across recent releases but undocumented).
            c4d.CallCommand(100004769)
        except Exception:
            pass

        bd = self.doc.GetActiveBaseDraw()
        cam = None
        if bd is not None:
            cam = bd.GetSceneCamera(self.doc) or bd.GetEditorCamera()
        if cam is not None:
            mg = op.GetMg()
            center = mg * op.GetMp()          # world center of the bounding box
            rad = op.GetRad()                 # half extent (local)
            sx, sy, sz = mg.v1.GetLength(), mg.v2.GetLength(), mg.v3.GetLength()
            r = max(rad.x * sx, rad.y * sy, rad.z * sz)
            if r <= 0:                        # null/spline/camera without volume
                r = 100.0
            cm = cam.GetMg()
            forward = cm.v3                   # keep viewing direction (+z)
            dist = r * 2.8                    # fit the sphere comfortably
            cm.off = center - forward * dist
            cam.SetMg(cm)

        c4d.EventAdd()
        try:
            c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
        except Exception:
            pass
        return True

    def _used_material_names(self) -> set:
        """Names of all materials assigned via texture tags.

        Usage tracked by NAME (wrapper identity/id() is not stable, same as
        with the selection). Best-effort.
        """
        used_names: set = set()

        def visit(op):
            while op:
                try:
                    for tag in op.GetTags():
                        if tag.IsInstanceOf(c4d.Ttexture):
                            m = tag.GetMaterial()
                            if m is not None:
                                used_names.add(m.GetName())
                except Exception:
                    pass
                visit(op.GetDown())
                op = op.GetNext()

        visit(self.doc.GetFirstObject())
        return used_names

    def scan_materials(self) -> dict:
        """Material overview: total, unused, missing textures."""
        import os
        doc = self.doc
        try:
            mats = doc.GetMaterials()
        except Exception:
            return {"total": 0, "unused": [], "missing": [], "missing_textures": 0}

        used_names = self._used_material_names()
        doc_path = doc.GetDocumentPath() or ""
        unused: list = []
        missing: list = []
        for m in mats:
            name = m.GetName()
            if name not in used_names:
                unused.append(name)
            try:
                sh = m.GetFirstShader()
                while sh:
                    if sh.IsInstanceOf(c4d.Xbitmap):
                        fn = sh[c4d.BITMAPSHADER_FILENAME]
                        if fn:
                            resolved = c4d.GenerateTexturePath(doc_path, fn, "")
                            if not resolved or not os.path.isfile(resolved):
                                missing.append({"material": name,
                                                "file": os.path.basename(str(fn))})
                    sh = sh.GetNext()
            except Exception:
                pass

        return {
            "total": len(mats),
            "unused": unused,
            "missing": missing[:50],
            "missing_textures": len(missing),
        }

    def delete_material(self, name: str) -> int:
        """Deletes unused materials with this name (undoable).

        Safety: removes ONLY materials that are currently not assigned to any
        texture tag -- even if a material with the same name is in use, the
        used one remains untouched.
        """
        doc = self.doc
        used_names = self._used_material_names()
        if name in used_names:
            return 0
        targets = [m for m in doc.GetMaterials() if m.GetName() == name]
        if not targets:
            return 0
        doc.StartUndo()
        for m in targets:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, m)
            m.Remove()
        doc.EndUndo()
        c4d.EventAdd()
        return len(targets)

    def delete_unused_materials(self) -> int:
        """Deletes ALL currently unused materials in ONE undo step.

        Unused = not assigned to any texture tag (name comparison). A used
        material with the same name remains untouched.
        """
        doc = self.doc
        used_names = self._used_material_names()
        targets = [m for m in doc.GetMaterials() if m.GetName() not in used_names]
        if not targets:
            return 0
        doc.StartUndo()
        for m in targets:
            doc.AddUndo(c4d.UNDOTYPE_DELETE, m)
            m.Remove()
        doc.EndUndo()
        c4d.EventAdd()
        return len(targets)

    # -- Writing ----------------------------------------------------------
    def _find_or_create_group(self, name: str, created: list[object]) -> object:
        top = self.doc.GetFirstObject()
        while top:
            if top.CheckType(c4d.Onull) and top.GetName() == name:
                return top
            top = top.GetNext()
        null = c4d.BaseObject(c4d.Onull)
        null.SetName(name)
        self.doc.InsertObject(null)
        self.doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, null)
        created.append(null)
        return null

    def apply_renames(self, renames: list[RenameOp]) -> int:
        if not renames:
            return 0
        self.doc.StartUndo()
        count = 0
        for op in renames:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetName(op.new_name)
            count += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    def _find_or_create_layer(self, name: str, created: list, cache: dict):
        if name in cache:
            return cache[name]
        root = self.doc.GetLayerObjectRoot()
        lay = root.GetDown()
        while lay:
            if lay.GetName() == name:
                cache[name] = lay
                return lay
            lay = lay.GetNext()
        layer = c4d.documents.LayerObject()
        layer.SetName(name)
        col = LAYER_COLORS.get(name)
        if col is not None:
            try:
                layer[c4d.ID_LAYER_COLOR] = c4d.Vector(*col)
            except Exception:
                pass
        layer.InsertUnder(root)
        self.doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, layer)
        created.append(layer)
        cache[name] = layer
        return layer

    def apply_layers(self, layerops: list[LayerOp]) -> int:
        """Assigns layers to objects (type axis) without changing the hierarchy.

        Layers are created on demand (colored). Changes ONLY the layer
        assignment -> the spatial null structure remains fully untouched.
        """
        if not layerops:
            return 0
        self.doc.StartUndo()
        created: list = []
        cache: dict = {}
        count = 0
        for op in layerops:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            layer = self._find_or_create_layer(op.layer, created, cache)
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetLayerObject(layer)
            count += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    def apply_reparents(self, reparents: list[ReparentOp]) -> int:
        if not reparents:
            return 0
        self.doc.StartUndo()
        created: list[object] = []
        count = 0
        for op in reparents:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            group = self._find_or_create_group(op.to_group, created)
            if obj == group:
                continue
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            mg = obj.GetMg()
            obj.Remove()
            obj.InsertUnderLast(group)
            obj.SetMg(mg)  # keep world position
            count += 1
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    # -- Restructuring plan (written by the skill) ------------------------
    def apply_plan(self, operations: list[dict]) -> dict:
        """Executes a deterministic restructuring plan (1 undo step).

        Operations (order matters). `target`/`under`/`into` reference either
        an existing `guid` (int, from the export) OR a plan-local `$id` of a
        group created earlier in this plan (str):

          {"op": "group",  "id": "$gf", "name": "GROUND_FLOOR", "under": 12}
          {"op": "rename", "target": 40, "to": "KITCHEN_WINDOW"}
          {"op": "move",   "target": 40, "into": "$gf"}
          {"op": "layer",  "target": 40, "layer": "Lights"}

        After this call, build_tree() must run again (guids are stale).
        """
        refs: dict = {}          # "$id" -> created object
        created: list = []
        lay_cache: dict = {}
        applied: collections.Counter = collections.Counter()
        errors: list = []

        def resolve(ref):
            if ref is None:
                return None
            if isinstance(ref, str) and ref.startswith("$"):
                return refs.get(ref)
            return self._by_guid.get(ref)

        self.doc.StartUndo()
        for i, opd in enumerate(operations):
            kind = opd.get("op")
            try:
                if kind == "group":
                    null = c4d.BaseObject(c4d.Onull)
                    null.SetName(opd.get("name", "GROUP"))
                    parent = resolve(opd.get("under"))
                    if parent is not None:
                        null.InsertUnderLast(parent)
                    else:
                        self.doc.InsertObject(null)
                    self.doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, null)
                    created.append(null)
                    if opd.get("id"):
                        refs[opd["id"]] = null
                    applied["group"] += 1
                elif kind == "rename":
                    obj = resolve(opd.get("target"))
                    if obj is None:
                        errors.append("rename #%d: target missing" % i)
                        continue
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    obj.SetName(opd.get("to", obj.GetName()))
                    applied["rename"] += 1
                elif kind == "move":
                    obj = resolve(opd.get("target"))
                    dest = resolve(opd.get("into"))
                    if obj is None:
                        errors.append("move #%d: target missing" % i)
                        continue
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    mg = obj.GetMg()
                    obj.Remove()
                    if dest is not None:
                        obj.InsertUnderLast(dest)
                    else:
                        self.doc.InsertObject(obj)
                    obj.SetMg(mg)
                    applied["move"] += 1
                elif kind == "layer":
                    obj = resolve(opd.get("target"))
                    if obj is None:
                        errors.append("layer #%d: target missing" % i)
                        continue
                    layer = self._find_or_create_layer(
                        opd.get("layer", "Layer"), created, lay_cache)
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    obj.SetLayerObject(layer)
                    applied["layer"] += 1
                else:
                    errors.append("op #%d: unknown '%s'" % (i, kind))
            except Exception as ex:  # noqa: BLE001
                errors.append("op #%d (%s): %s" % (i, kind, ex))
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"applied": dict(applied), "errors": errors,
                "total": sum(applied.values())}
