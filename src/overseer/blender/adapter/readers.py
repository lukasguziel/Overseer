"""Per-object bpy readers: classification, type label, geometry, visibility,
owning collection. The Blender twin of cinema/adapter/readers.py.

Only pure-ish ``bpy`` reads live here; they are called by ``scene.py``'s
``build_tree``. Every read is defensive - a huge production scene has objects
in odd states and a single raise must not abort the whole tree walk.
"""
from __future__ import annotations

from ...core import model
from ..constants import CATEGORY_BY_TYPE, TYPE_LABELS


def type_name(obj) -> str:
    try:
        return TYPE_LABELS.get(obj.type, obj.type.title())
    except Exception:
        return "Object"


def classify(obj) -> str:
    try:
        return CATEGORY_BY_TYPE.get(obj.type, model.CAT_OTHER)
    except Exception:
        return model.CAT_OTHER


def stable_id(obj) -> int:
    """Session-stable identity (parity with C4D ``GetGUID``)."""
    try:
        return int(obj.session_uid)
    except Exception:
        try:
            return id(obj)
        except Exception:
            return 0


def own_geo(obj, depsgraph=None) -> tuple:
    """(point_count, poly_count) of the *evaluated* object - i.e. after
    modifiers / geometry nodes, the analog of C4D's cache/deform-cache geo.

    Uses the depsgraph-evaluated mesh so a Subdivision Surface or Array
    modifier is reflected, then clears the temporary mesh.
    """
    try:
        if obj.type not in ("MESH", "CURVE", "SURFACE", "FONT", "META"):
            return 0, 0
    except Exception:
        return 0, 0
    eval_obj = obj
    try:
        if depsgraph is not None:
            eval_obj = obj.evaluated_get(depsgraph)
    except Exception:
        eval_obj = obj
    mesh = None
    try:
        mesh = eval_obj.to_mesh()
        if mesh is None:
            return 0, 0
        pts = len(mesh.vertices)
        polys = len(mesh.polygons)
        return pts, polys
    except Exception:
        return 0, 0
    finally:
        if mesh is not None:
            try:
                eval_obj.to_mesh_clear()
            except Exception:
                pass


def editor_hidden(obj, hidden_ancestor: bool = False) -> bool:
    """True when the object is hidden in the viewport."""
    try:
        # visible_get folds in collection exclusion + hide flags for the
        # active view layer; fall back to the raw hide flag if it raises.
        return not bool(obj.visible_get())
    except Exception:
        try:
            return bool(obj.hide_viewport) or hidden_ancestor
        except Exception:
            return hidden_ancestor


def layer_name(obj, master=None) -> str | None:
    """The object's owning "layer" = its first collection that is not the
    scene master collection. Blender collections are the layer analog."""
    try:
        cols = obj.users_collection
    except Exception:
        return None
    for c in cols:
        try:
            if master is not None and c == master:
                continue
            name = c.name
            if name:
                return name
        except Exception:
            continue
    return None
