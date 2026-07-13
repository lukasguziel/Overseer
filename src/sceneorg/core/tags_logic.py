from __future__ import annotations

import math

DEFAULT_PHONG_ANGLE_DEG = 40.0

SELECTION_LABEL = "Selection"


def deg_from_rad(rad: float) -> float:
    return round(math.degrees(rad), 1)


def dominant_angle(counts: dict) -> float | None:
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def merge_selection_types(type_list: list, kind_by_type: dict) -> list:
    """Fold the point/polygon/edge selection tag types into ONE "Selection"
    entry: each object appears once, its tags stamped with their selection
    kind ("point"/"polygon"/"edge"), and the entry carries every source id in
    "type_ids" so select-in-C4D can cover all three.

    Entries look like {type_id, label, count, objects:[{guid, name,
    tags:[{name, kind?}]}]}; non-selection entries pass through untouched.
    The result is re-sorted by (-count, label).
    """
    selection = [e for e in type_list if e["type_id"] in kind_by_type]
    rest = [e for e in type_list if e["type_id"] not in kind_by_type]
    if not selection:
        return type_list

    by_guid: dict = {}
    order: list = []
    for entry in selection:
        kind = kind_by_type[entry["type_id"]]
        for obj in entry["objects"]:
            merged = by_guid.get(obj["guid"])
            if merged is None:
                merged = {"guid": obj["guid"], "name": obj["name"], "tags": []}
                by_guid[obj["guid"]] = merged
                order.append(merged)
            for tag in obj["tags"]:
                merged["tags"].append(dict(tag, kind=kind))

    merged_entry = {
        "type_id": min(e["type_id"] for e in selection),
        "type_ids": sorted(e["type_id"] for e in selection),
        "label": SELECTION_LABEL,
        "count": sum(e["count"] for e in selection),
        "objects": order,
    }
    return sorted(rest + [merged_entry],
                  key=lambda e: (-e["count"], e["label"]))
