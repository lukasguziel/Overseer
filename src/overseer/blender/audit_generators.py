"""Generators audit for Blender.

A C4D "generator" (Subdivision Surface, Cloner, Extrude, Instance, Symmetry)
is a distinct object *type*; in Blender the same modelling power lives in
**modifiers** (Subdivision Surface, Array, Mirror, Solidify, Screw, Bevel,
Boolean, ...), in **Geometry Nodes** modifiers, and in object **instancing**
(``object.instance_type``). One object can carry several modifiers, so a
"generator" here is a single *modifier instance* (or an instancing object),
grouped by kind.

The result shape is the C4D one (see ``cinema/audit_generators.py`` and the
frozen ``frontend/src/tabs/GeneratorsTab.tsx``): ``types`` -> per-type param
cards, each param summarised across its members via ``core.gens_logic``.
GeneratorsTab reads ``data.types`` and ``data.summary`` verbatim, so we return
those keys (NOT a flat ``generators`` list).

Declarative ``_REGISTRY`` maps a modifier ``type`` to the attributes to
surface; nothing is hand-tabled beyond the attribute *names*: every human
label (the modifier type name, each parameter label, every dropdown option)
is read from ``holder.bl_rna`` at scan time, exactly like the C4D build reads
labels from the object description. Modifier types not in the registry still
appear (as paramless cards) so the audit covers *every* modifier; Geometry
Nodes modifiers group by node-group name; instancing objects form one group.

No top-level ``import bpy`` - Blender objects arrive via ``adapter._by_guid``
and ``adapter.bpy``; every attribute access is defensive.
"""
from __future__ import annotations

from ..core import gens_logic

# Curated per-modifier-type parameter lists. Each entry: (attr, kind) where
# kind is the FRONTEND ParamKind ('int' | 'bool' | 'choice'). Blender has no
# separate float kind, so continuous floats (thickness, angle, ...) also use
# 'int' - the UI renders a free numeric input for them and we coerce back to
# the real property type on apply (never truncating). Labels are NOT stored
# here; they are read from bl_rna.
_REGISTRY = [
    {"key": "subsurf", "mod_type": "SUBSURF", "params": [
        ("levels", "int"), ("render_levels", "int"),
        ("subdivision_type", "choice"), ("use_limit_surface", "bool")]},
    {"key": "array", "mod_type": "ARRAY", "params": [
        ("fit_type", "choice"), ("count", "int"),
        ("use_relative_offset", "bool"), ("use_merge_vertices", "bool")]},
    {"key": "mirror", "mod_type": "MIRROR", "params": [
        ("use_clip", "bool"), ("use_mirror_merge", "bool"),
        ("merge_threshold", "int")]},
    {"key": "solidify", "mod_type": "SOLIDIFY", "params": [
        ("thickness", "int"), ("offset", "int"),
        ("solidify_mode", "choice"), ("use_even_offset", "bool")]},
    {"key": "screw", "mod_type": "SCREW", "params": [
        ("angle", "int"), ("steps", "int"), ("render_steps", "int"),
        ("screw_offset", "int"), ("use_smooth_shade", "bool")]},
    {"key": "bevel", "mod_type": "BEVEL", "params": [
        ("width", "int"), ("segments", "int"),
        ("limit_method", "choice"), ("affect", "choice")]},
    {"key": "boolean", "mod_type": "BOOLEAN", "params": [
        ("operation", "choice"), ("solver", "choice")]},
]

_BY_TYPE = {e["mod_type"]: e for e in _REGISTRY}

# Instancing is a per-object generator (not a modifier). Its holder is the
# object itself; the enum label for each value is read from the object bl_rna.
_INSTANCE_KEY = "instance"
_INSTANCE_LABEL = "Instancing"
_INSTANCE_PARAMS = [("instance_type", "choice")]


# ---------------------------------------------------------------------------
# introspection helpers (all read labels from bl_rna, never hand-tabled)
# ---------------------------------------------------------------------------
def _jsonify(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, str):
        return value
    # bpy vectors / bool arrays / colours -> plain list of rounded floats.
    try:
        return [round(float(x), 4) for x in value]
    except Exception:
        return str(value)


def _read(holder, attr):
    """Current value of ``attr`` on a modifier or object, JSON-safe."""
    try:
        return _jsonify(getattr(holder, attr))
    except Exception:
        return None


def _prop_type(holder, attr):
    try:
        return holder.bl_rna.properties[attr].type
    except Exception:
        return None


def _coerce(holder, attr, value):
    """Coerce an incoming JSON value to the property's real Blender type, so a
    float parameter that the UI edits as a number is never truncated."""
    ptype = _prop_type(holder, attr)
    if ptype == "BOOLEAN":
        return bool(value)
    if ptype == "INT":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if ptype == "FLOAT":
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if ptype == "ENUM":
        return str(value)
    return value


def _param_label(holder, attr):
    try:
        return holder.bl_rna.properties[attr].name or attr
    except Exception:
        return attr


def _enum_choices(holder, attr):
    """{enum_identifier: human name} read from bl_rna - never hand-tabled."""
    out = {}
    try:
        for item in holder.bl_rna.properties[attr].enum_items:
            ident = str(item.identifier)
            out[ident] = item.name or ident
    except Exception:
        pass
    return out


def _mod_type_label(mod):
    """Human name of the modifier's own type, from the ``type`` enum."""
    try:
        return mod.bl_rna.properties["type"].enum_items[mod.type].name or mod.type
    except Exception:
        try:
            return str(mod.type)
        except Exception:
            return "Modifier"


def _type_id(key: str) -> int:
    """Stable non-negative int per group key (the frozen UI types type_id as a
    number; Blender has no numeric modifier id, so we hash the group key).
    Only used for the icon-cache key, so a hash is sufficient."""
    h = 2166136261
    for ch in key:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h & 0x7FFFFFFF


def _group_for_mod(mod):
    """(group_key, label, params_def) for a modifier, or None to skip.

    Geometry Nodes group by node-group name; registry types use their curated
    params; any other modifier still appears, with no editable params."""
    try:
        mtype = mod.type
    except Exception:
        return None
    if mtype == "NODES":
        gname = ""
        try:
            ng = getattr(mod, "node_group", None)
            gname = ng.name if ng is not None else ""
        except Exception:
            gname = ""
        return ("nodes:" + gname, gname or "Geometry Nodes", [])
    label = _mod_type_label(mod)
    entry = _BY_TYPE.get(mtype)
    if entry is not None:
        return (entry["key"], label, entry["params"])
    return ("mod:" + str(mtype), label, [])


def _instance_type(obj):
    try:
        return getattr(obj, "instance_type", "NONE")
    except Exception:
        return "NONE"


def _is_instancing(obj) -> bool:
    return _instance_type(obj) not in ("NONE", "", None)


# ---------------------------------------------------------------------------
# tab visibility
# ---------------------------------------------------------------------------
def has_any(adapter, tree) -> bool:
    for node in tree.walk():
        obj = adapter._by_guid.get(node.guid)
        if obj is None:
            continue
        try:
            if len(obj.modifiers) > 0:
                return True
        except Exception:
            pass
        if _is_instancing(obj):
            return True
    return False


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------
def _scan(payload, doc, adapter, tree, progress):
    groups = {}  # key -> {"label", "params_def", "members": [(node, holder)]}
    nodes = list(tree.walk())
    total = len(nodes)
    for i, node in enumerate(nodes):
        if progress and i % 200 == 0:
            progress("Scanning generators", i, total, node.name)
        obj = adapter._by_guid.get(node.guid)
        if obj is None:
            continue
        try:
            mods = list(obj.modifiers)
        except Exception:
            mods = []
        for mod in mods:
            g = _group_for_mod(mod)
            if g is None:
                continue
            key, label, params_def = g
            bucket = groups.setdefault(
                key, {"label": label, "params_def": params_def, "members": []})
            bucket["members"].append((node, mod))
        if _is_instancing(obj):
            bucket = groups.setdefault(
                _INSTANCE_KEY,
                {"label": _INSTANCE_LABEL, "params_def": _INSTANCE_PARAMS,
                 "members": []})
            bucket["members"].append((node, obj))

    types_out = []
    non_uniform_params = 0
    total_gens = 0
    for key, bucket in groups.items():
        members = bucket["members"]
        total_gens += len(members)
        params_out = []
        for attr, kind in bucket["params_def"]:
            entries = []
            for node, holder in members:
                value = _read(holder, attr)
                if value is None:
                    continue
                entries.append({"guid": node.guid, "name": node.name,
                                "value": value})
            summary = gens_logic.summarize(entries)
            if not summary["uniform"]:
                non_uniform_params += 1
            choices = {}
            label = attr
            if members:
                first_holder = members[0][1]
                label = _param_label(first_holder, attr)
                if kind == "choice":
                    choices = _enum_choices(first_holder, attr)
            params_out.append({
                "key": attr, "label": label, "kind": kind,
                "choices": choices,
                "values": summary["values"],
                "distribution": summary["distribution"],
                "uniform": summary["uniform"],
                "dominant": summary["dominant"],
                "outliers": summary["outliers"],
            })
        types_out.append({
            "key": key, "label": bucket["label"], "type_id": _type_id(key),
            "count": len(members), "params": params_out,
        })

    types_out.sort(key=lambda t: -t["count"])
    return {
        "ok": True,
        "types": types_out,
        "summary": {
            "total_generators": total_gens,
            "types_found": len(types_out),
            "non_uniform_params": non_uniform_params,
        },
    }


# ---------------------------------------------------------------------------
# apply / select
# ---------------------------------------------------------------------------
def _members_of(adapter, tree, type_key, guids=None):
    """(node, holder) pairs for every member of ``type_key``. The holder is a
    modifier for modifier groups, the object itself for the instancing group -
    matching what ``_read`` / ``_coerce`` operate on."""
    wanted = set(guids) if guids is not None else None
    out = []
    for node in tree.walk():
        if wanted is not None and node.guid not in wanted:
            continue
        obj = adapter._by_guid.get(node.guid)
        if obj is None:
            continue
        if type_key == _INSTANCE_KEY:
            if _is_instancing(obj):
                out.append((node, obj))
            continue
        try:
            mods = list(obj.modifiers)
        except Exception:
            mods = []
        for mod in mods:
            g = _group_for_mod(mod)
            if g is not None and g[0] == type_key:
                out.append((node, mod))
    return out


def _apply(payload, doc, adapter, tree, progress):
    type_key = payload.get("type_key")
    param_key = payload.get("param_key")
    value = payload.get("value")
    guids = payload.get("guids")
    if not type_key or not param_key:
        return {"error": "missing type_key/param_key"}

    members = _members_of(adapter, tree, type_key, guids)
    applied = 0
    for _node, holder in members:
        try:
            setattr(holder, param_key, _coerce(holder, param_key, value))
            applied += 1
        except Exception:
            pass

    if applied:
        doc.undo_push("Overseer: align generators")
        doc.tag_redraw()
    return {"ok": True, "applied": applied}


def _select_guids(adapter, doc, guids):
    bpy = adapter.bpy
    try:
        for o in doc.selected_objects():
            o.select_set(False)
    except Exception:
        pass
    selected = 0
    active = None
    for guid in guids:
        obj = adapter._by_guid.get(guid)
        if obj is None:
            continue
        try:
            obj.select_set(True)
            active = obj
            selected += 1
        except Exception:
            pass
    if active is not None:
        try:
            bpy.context.view_layer.objects.active = active
        except Exception:
            pass
    doc.tag_redraw()
    return selected


def _select(payload, doc, adapter, tree, progress):
    type_key = payload.get("type_key")
    param_key = payload.get("param_key")
    if not type_key:
        # Direct guid selection fallback (task contract); the frozen UI drives
        # selection by type/param/value, handled below.
        guids = payload.get("guids") or []
        return {"ok": True, "selected": _select_guids(adapter, doc, guids)}

    members = _members_of(adapter, tree, type_key)
    if param_key is not None and "value" in payload:
        wanted = gens_logic._hashable(payload.get("value"))
        members = [(n, h) for n, h in members
                   if gens_logic._hashable(_read(h, param_key)) == wanted]

    guids = []
    seen = set()
    for node, _holder in members:
        if node.guid not in seen:
            seen.add(node.guid)
            guids.append(node.guid)
    return {"ok": True, "selected": _select_guids(adapter, doc, guids)}


def handle(op, payload, doc, adapter, tree, progress):
    if op == "gens_scan":
        return _scan(payload, doc, adapter, tree, progress)
    if op == "gens_apply":
        return _apply(payload, doc, adapter, tree, progress)
    if op == "gens_select":
        return _select(payload, doc, adapter, tree, progress)
    return {"error": "unknown gens op: %s" % op}
