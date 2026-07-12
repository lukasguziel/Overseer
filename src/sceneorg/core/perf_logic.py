"""Pure ranking logic for the generator performance audit.

The host measures how long ONE object takes to rebuild its cache (see
cinema/audit_perf.py); everything that turns those raw milliseconds into a
verdict lives here, so it is testable without Cinema 4D.
"""
from __future__ import annotations

# A rebuild below this is noise — timer jitter, not a cost worth showing.
NOISE_MS = 0.5

# Share of the measured total from which an object counts as the bottleneck /
# a heavy contributor. Relative, because "slow" only means anything next to
# the rest of the scene.
HEAVY_SHARE = 0.25
MID_SHARE = 0.08


def level_for(share: float, ms: float) -> str:
    """heavy | mid | light — how much this object hurts the viewport."""
    if ms < NOISE_MS:
        return "light"
    if share >= HEAVY_SHARE:
        return "heavy"
    if share >= MID_SHARE:
        return "mid"
    return "light"


def rank(entries: list) -> dict:
    """Sort measurements slowest first and attach share + level.

    entries: [{"guid", "name", "type", "ms", "polygons"}, ...]
    """
    rows = [dict(e) for e in entries]
    total = sum(max(0.0, float(r.get("ms") or 0.0)) for r in rows)
    for r in rows:
        ms = max(0.0, float(r.get("ms") or 0.0))
        r["ms"] = ms
        r["share"] = (ms / total) if total > 0 else 0.0
        r["level"] = level_for(r["share"], ms)
    rows.sort(key=lambda r: -r["ms"])

    heavy = [r for r in rows if r["level"] == "heavy"]
    measurable = [r for r in rows if r["ms"] >= NOISE_MS]
    # The single worst offender, but only when it is genuinely dominant —
    # a scene where everything costs the same has no bottleneck to name.
    top = rows[0] if rows and rows[0]["level"] == "heavy" else None
    return {
        "entries": rows,
        "summary": {
            "total": len(rows),
            "measured": len(measurable),
            "total_ms": total,
            "heavy": len(heavy),
            "slowest": top["name"] if top else "",
            "slowest_ms": top["ms"] if top else 0.0,
            "slowest_share": top["share"] if top else 0.0,
        },
    }
