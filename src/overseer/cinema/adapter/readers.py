from __future__ import annotations

import c4d

from ...core import model
from ...core.defaults import RS_CAMERA_IDS, RS_LIGHT_IDS
from ..constants import KNOWN_TYPES


def _save_filters() -> dict:
    table = {
        (".png",): "FILTER_PNG",
        (".jpg", ".jpeg"): "FILTER_JPG",
        (".tif", ".tiff"): "FILTER_TIF",
        (".bmp",): "FILTER_BMP",
        (".tga",): "FILTER_TGA",
        (".psd",): "FILTER_PSD",
        (".exr",): "FILTER_EXR",
        (".hdr",): "FILTER_HDR",
    }
    out: dict = {}
    for exts, sym in table.items():
        fid = getattr(c4d, sym, None)
        if fid is None:
            continue
        for ext in exts:
            out[ext] = fid
    return out


_SAVE_FILTERS = _save_filters()


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


def _is_control_object(op) -> bool:
    try:
        return bool(op.GetBit(c4d.BIT_CONTROLOBJECT))
    except Exception:
        return False


def _virtual_geo(op) -> tuple:
    """Geometry of a cache subtree as (pts, polys, ctrl_pts, ctrl_polys).

    Polygon objects flagged BIT_CONTROLOBJECT are tallied separately: the
    flag normally marks the generator INPUTS duplicated into the cache
    (counting them would double the geometry) — but C4D 2026 flags the
    generated result meshes too, so a Sweep/Symmetry cache holds ONLY
    control-marked polys and the plain count comes back 0. The caller
    falls back to the ctrl tally exactly then — a fallback can never
    double count against a zero.
    """
    pts = polys = cpts = cpolys = 0
    o = op
    while o:
        dc = o.GetDeformCache()
        c = o.GetCache() if dc is None else None
        if dc:
            p2, q2, cp2, cq2 = _virtual_geo(dc)
            pts += p2
            polys += q2
            cpts += cp2
            cpolys += cq2
        elif c:
            p2, q2, cp2, cq2 = _virtual_geo(c)
            pts += p2
            polys += q2
            cpts += cp2
            cpolys += cq2
        elif o.IsInstanceOf(c4d.Opolygon):
            try:
                if _is_control_object(o):
                    cpts += o.GetPointCount()
                    cpolys += o.GetPolygonCount()
                else:
                    pts += o.GetPointCount()
                    polys += o.GetPolygonCount()
            except Exception:
                pass
        down = o.GetDown()
        if down:
            p2, q2, cp2, cq2 = _virtual_geo(down)
            pts += p2
            polys += q2
            cpts += cp2
            cpolys += cq2
        o = o.GetNext()
    return pts, polys, cpts, cpolys


def own_geo(op, _depth: int = 0) -> tuple:
    if op.IsInstanceOf(c4d.Opolygon):
        try:
            return op.GetPointCount(), op.GetPolygonCount()
        except Exception:
            return 0, 0
    cache = op.GetDeformCache() or op.GetCache()
    if cache is not None:
        pts, polys, cpts, cpolys = _virtual_geo(cache)
        if pts or polys:
            return pts, polys
        if cpts or cpolys:
            return cpts, cpolys
    # Render instances build no cache at all — resolve the link and count
    # the referenced SUBTREE (the link often points at a null group; the
    # instance renders the whole branch). Depth-capped against link cycles
    # and instances nested under their own reference.
    if _depth < 8 and op.CheckType(c4d.Oinstance):
        try:
            ref = op[c4d.INSTANCEOBJECT_LINK]
        except Exception:
            ref = None
        if ref is not None:
            return _subtree_geo(ref, _depth + 1)
    return 0, 0


def _subtree_geo(op, _depth: int = 0) -> tuple:
    pts, polys = own_geo(op, _depth)
    child = op.GetDown()
    while child:
        p2, q2 = _subtree_geo(child, _depth)
        pts += p2
        polys += q2
        child = child.GetNext()
    return pts, polys


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


def layer_name(op) -> str | None:
    try:
        lay = op.GetLayerObject(op.GetDocument())
        return lay.GetName() if lay is not None else None
    except Exception:
        return None


def stable_id(op) -> int:
    try:
        return op.GetGUID()
    except Exception:
        return 0


def editor_visibility(op) -> int:
    try:
        return op[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR]
    except Exception:
        return c4d.MODE_UNDEF


def editor_hidden(op, hidden_ancestor: bool = False) -> bool:
    mode = editor_visibility(op)
    if mode == c4d.MODE_ON:
        return False
    if mode == c4d.MODE_OFF:
        return True
    return hidden_ancestor
