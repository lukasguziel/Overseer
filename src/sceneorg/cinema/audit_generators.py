from __future__ import annotations

import c4d

from ..core import gens_logic

_ENABLED = "enabled"

_REGISTRY = [
    {
        "key": "sds",
        "type_attr": "Osds",
        "label": "Subdivision Surface",
        "params": [
            {"key": "editor_sub",
             "attrs": ["SDSOBJECT_SUBEDITOR_CM", "SDSOBJECT_SUBEDITOR"],
             "label": "Editor subdivisions", "kind": "int"},
            {"key": "render_sub",
             "attrs": ["SDSOBJECT_SUBRAY_CM", "SDSOBJECT_SUBRAY"],
             "label": "Render subdivisions", "kind": "int"},
            {"key": "algo", "attrs": ["SDSOBJECT_TYPE"],
             "label": "Subdivision algorithm", "kind": "choice"},
        ],
    },
    {
        "key": "cloner",
        "type_id": 1018544,
        "label": "Cloner",
        "params": [
            {"key": "mode", "attrs": ["MG_CLONE_MODE", "ID_MG_CLONER_MODE"],
             "label": "Clone mode", "kind": "choice"},
        ],
    },
    {
        "key": "extrude",
        "type_attr": "Oextrude",
        "label": "Extrude",
        "params": [
            {"key": "subdivision",
             "attrs": ["EXTRUDEOBJECT_SUB", "EXTRUDEOBJECT_SUBDIVISION"],
             "label": "Subdivisions", "kind": "int"},
        ],
    },
    {
        "key": "instance",
        "type_attr": "Oinstance",
        "label": "Instance",
        "params": [
            {"key": "render_instance",
             "attrs": ["INSTANCEOBJECT_RENDERINSTANCE_MODE",
                       "INSTANCEOBJECT_RENDERINSTANCE"],
             "label": "Render instance", "kind": "choice"},
        ],
    },
    {
        "key": "symmetry",
        "type_attr": "Osymmetry",
        "label": "Symmetry",
        "params": [
            {"key": "plane", "attrs": ["SYMMETRYOBJECT_PLANE"],
             "label": "Mirror plane", "kind": "choice"},
        ],
    },
]


def _resolve_id(attrs):
    for name in attrs:
        pid = getattr(c4d, name, None)
        if isinstance(pid, int):
            return pid
    return None


def _resolve_registry():
    resolved = {}
    for entry in _REGISTRY:
        if "type_attr" in entry:
            type_id = getattr(c4d, entry["type_attr"], None)
        else:
            type_id = entry.get("type_id")
        if not isinstance(type_id, int):
            continue
        params = []
        for p in entry["params"]:
            pid = _resolve_id(p["attrs"])
            if pid is None:
                continue
            params.append({"key": p["key"], "label": p["label"],
                           "kind": p["kind"], "id": pid})
        params.append({"key": _ENABLED, "label": "Enabled",
                       "kind": "bool", "id": None})
        resolved[type_id] = {"key": entry["key"], "label": entry["label"],
                             "type_id": type_id, "params": params}
    return resolved


def _jsonify(value):
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, str):
        return value
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, c4d.Vector):
        return [round(value.x, 6), round(value.y, 6), round(value.z, 6)]
    return str(value)


def _read_param(obj, param):
    if param["id"] is None:
        try:
            return bool(obj.GetDeformMode())
        except Exception:
            return None
    try:
        return _jsonify(obj[param["id"]])
    except Exception:
        return None


def _coerce(value, kind):
    if kind == "bool":
        return bool(value)
    if kind == "int" or kind == "choice":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    return value


def _choice_labels(obj, pid) -> dict:
    """value -> human label for a cycle (dropdown) parameter, read from the
    object's OWN description — the exact strings C4D shows in the Attribute
    Manager, no hand-maintained tables."""
    try:
        description = obj.GetDescription(c4d.DESCFLAGS_DESC_NONE)
        for bc, paramid, _group in description:
            try:
                if paramid[0].id != pid:
                    continue
            except Exception:
                continue
            cycle = bc.GetContainerInstance(c4d.DESC_CYCLE)
            if cycle is None:
                return {}
            out = {}
            for cid, name in cycle:
                if isinstance(name, str) and name:
                    out[int(cid)] = name
            return out
    except Exception:
        pass
    return {}


def _objects_by_type(adapter, tree, progress=None):
    resolved = _resolve_registry()
    groups = {}
    nodes = list(tree.walk())
    total = len(nodes)
    for i, node in enumerate(nodes):
        if progress and i % 200 == 0:
            progress("Scanning generators", i, total, node.name)
        obj = adapter._by_guid.get(node.guid)
        if obj is None:
            continue
        try:
            type_id = obj.GetType()
        except Exception:
            continue
        entry = resolved.get(type_id)
        if entry is None:
            continue
        groups.setdefault(type_id, []).append((node, obj))
    return resolved, groups


def _scan(payload, doc, adapter, tree, progress):
    resolved, groups = _objects_by_type(adapter, tree, progress)

    types_out = []
    non_uniform_params = 0
    total_gens = 0
    for type_id, members in groups.items():
        entry = resolved[type_id]
        total_gens += len(members)
        params_out = []
        for param in entry["params"]:
            entries = []
            for node, obj in members:
                value = _read_param(obj, param)
                if value is None:
                    continue
                entries.append({"guid": node.guid, "name": node.name,
                                "value": value})
            summary = gens_logic.summarize(entries)
            if not summary["uniform"]:
                non_uniform_params += 1
            # Human labels for dropdown values, straight from C4D's own
            # description (e.g. 2102 -> "Catmull-Clark (N-Gons)").
            choices = {}
            if param["kind"] == "choice" and param["id"] is not None and members:
                labels = _choice_labels(members[0][1], param["id"])
                choices = {str(k): v for k, v in labels.items()}
            params_out.append({
                "key": param["key"], "label": param["label"],
                "kind": param["kind"],
                "choices": choices,
                "values": summary["values"],
                "distribution": summary["distribution"],
                "uniform": summary["uniform"],
                "dominant": summary["dominant"],
                "outliers": summary["outliers"],
            })
        types_out.append({"key": entry["key"], "label": entry["label"],
                          "type_id": type_id,
                          "count": len(members), "params": params_out})

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


def _entry_and_param(type_key, param_key):
    resolved = _resolve_registry()
    for entry in resolved.values():
        if entry["key"] != type_key:
            continue
        for param in entry["params"]:
            if param["key"] == param_key:
                return entry, param
        return entry, None
    return None, None


def _members_of(adapter, tree, type_id, guids=None):
    wanted = set(guids) if guids is not None else None
    out = []
    for node in tree.walk():
        if wanted is not None and node.guid not in wanted:
            continue
        obj = adapter._by_guid.get(node.guid)
        if obj is None:
            continue
        try:
            if obj.GetType() != type_id:
                continue
        except Exception:
            continue
        out.append((node, obj))
    return out


def _apply(payload, doc, adapter, tree, progress):
    type_key = payload.get("type_key")
    param_key = payload.get("param_key")
    value = payload.get("value")
    guids = payload.get("guids")

    entry, param = _entry_and_param(type_key, param_key)
    if entry is None or param is None:
        return {"error": "unknown generator param: %s.%s" % (type_key, param_key)}

    members = _members_of(adapter, tree, entry["type_id"], guids)
    coerced = _coerce(value, param["kind"])

    doc.StartUndo()
    applied = 0
    for _node, obj in members:
        doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
        try:
            if param["id"] is None:
                obj.SetDeformMode(bool(coerced))
            else:
                obj[param["id"]] = coerced
            applied += 1
        except Exception:
            pass
    doc.EndUndo()
    c4d.EventAdd()
    return {"ok": True, "applied": applied}


def _select(payload, doc, adapter, tree, progress):
    type_key = payload.get("type_key")
    param_key = payload.get("param_key")
    want_value = payload.get("value")

    entry, param = _entry_and_param(type_key, param_key) if param_key \
        else (_entry_and_param(type_key, None)[0], None)
    if entry is None:
        return {"error": "unknown generator type: %s" % type_key}

    members = _members_of(adapter, tree, entry["type_id"])
    if param is not None:
        wanted = gens_logic._hashable(want_value)
        members = [(n, o) for n, o in members
                   if gens_logic._hashable(_read_param(o, param)) == wanted]

    selected = 0
    for _node, obj in members:
        mode = c4d.SELECTION_NEW if selected == 0 else c4d.SELECTION_ADD
        try:
            doc.SetActiveObject(obj, mode)
            obj.SetBit(c4d.BIT_ACTIVE)
            selected += 1
        except Exception:
            pass
    c4d.EventAdd()
    return {"ok": True, "selected": selected}


def handle(op, payload, doc, adapter, tree, progress):
    if op == "gens_scan":
        return _scan(payload, doc, adapter, tree, progress)
    if op == "gens_apply":
        return _apply(payload, doc, adapter, tree, progress)
    if op == "gens_select":
        return _select(payload, doc, adapter, tree, progress)
    return {"error": "unknown op: %s" % op}
