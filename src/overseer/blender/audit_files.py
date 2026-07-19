"""External-file audit for Blender - linked libraries (bpy.data.libraries),
images, cache files (.abc/.usd/.mdd/.pc2), sounds, fonts, volumes. STUB:
implemented by a dedicated subagent.

Reference: cinema/audit_files.py + core/files_logic.py. Drop the .blend's own
path; prefer blend-relative form. Ops: files_scan, files_make_relative,
files_select, files_pick_path, files_relink. Mirror shapes.
"""
from __future__ import annotations


def handle(op, payload, doc, adapter, tree, progress):
    if op == "files_scan":
        return {"ok": True, "files": [], "summary": {}}
    return {"error": "unknown files op: %s" % op}
