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


def type_entry(type_id, label: str) -> dict:
    return {"type_id": type_id, "label": label, "count": 0, "objects": []}


def object_row(guid: int, name: str, tags: list) -> dict:
    return {"guid": guid, "name": name, "tags": tags}


def scan_result(types: dict, missing_phong: list, duplicate_material_tags: list,
                phong_angles: dict, selection_kinds: dict | None = None,
                phong: bool = True) -> dict:
    type_list = sorted(types.values(), key=lambda e: (-e["count"], e["label"]))
    if selection_kinds:
        type_list = merge_selection_types(type_list, selection_kinds)
    dominant = dominant_angle(phong_angles)
    angle_dist = [{"angle_deg": deg, "count": n}
                  for deg, n in sorted(phong_angles.items())]
    total_tags = sum(e["count"] for e in types.values())
    out = {
        "ok": True,
        "types": type_list,
        "findings": {
            "missing_phong": missing_phong,
            "duplicate_material_tags": duplicate_material_tags,
            "phong_angles": {
                "distribution": angle_dist,
                "dominant_angle": dominant,
            },
        },
        "summary": {
            "total_tags": total_tags,
            "tag_types": len(type_list),
            "missing_phong": len(missing_phong),
            "duplicate_material_tags": len(duplicate_material_tags),
        },
    }
    if not phong:
        out["phong"] = False
    return out
