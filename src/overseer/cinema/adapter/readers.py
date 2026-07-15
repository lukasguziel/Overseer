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
    pts = polys = 0
    o = op
    while o:
        dc = o.GetDeformCache()
        c = o.GetCache() if dc is None else None
        if dc:
            p2, q2 = _virtual_geo(dc)
            pts += p2
            polys += q2
        elif c:
            p2, q2 = _virtual_geo(c)
            pts += p2
            polys += q2
        elif o.IsInstanceOf(c4d.Opolygon) and not _is_control_object(o):
            try:
                pts += o.GetPointCount()
                polys += o.GetPolygonCount()
            except Exception:
                pass
        down = o.GetDown()
        if down:
            p2, q2 = _virtual_geo(down)
            pts += p2
            polys += q2
        o = o.GetNext()
    return pts, polys


def own_geo(op) -> tuple:
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
