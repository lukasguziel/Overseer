"""Viewport-cost audit for Blender - which object/modifier stalls depsgraph
re-evaluation. STUB: implemented by a dedicated subagent.

Reference: cinema/audit_perf.py + core/perf_logic.py. Tag one object for update
(``obj.update_tag()``), time ``depsgraph.update()``; subtract the idle-pass
cost, take the median of N runs. Expensive - only on an explicit click. Op:
perf_scan, perf_select. Mirror shapes.
"""
from __future__ import annotations


def handle(op, payload, doc, adapter, tree, progress):
    if op == "perf_scan":
        return {"ok": True, "items": [], "summary": {}}
    return {"error": "unknown perf op: %s" % op}
