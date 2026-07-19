"""Tags audit for Blender - there are no C4D "tags"; we audit object
attachments: modifiers, constraints, custom properties, and mesh smoothing
(the Phong analog). STUB: implemented by a dedicated subagent.

Reference: cinema/audit_tags.py + core/tags_logic.py. Mirror the result shapes
(``types``/``findings``/``summary``). Ops: tags_scan, tags_add_phong (=>
shade-smooth / auto-smooth), tags_set_phong_angle (=> auto-smooth angle),
tags_delete_duplicates (=> collapse duplicate material slots), tags_select.
"""
from __future__ import annotations


def handle(op, payload, doc, adapter, tree, progress):
    if op == "tags_scan":
        return {"ok": True, "types": [], "findings": {}, "summary": {
            "total_tags": 0, "tag_types": 0, "missing_phong": 0,
            "duplicate_material_tags": 0}}
    return {"error": "unknown tags op: %s" % op}
