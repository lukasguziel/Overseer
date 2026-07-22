from __future__ import annotations

NOISE_MS = 0.5

HEAVY_SHARE = 0.25
MID_SHARE = 0.08


def level_for(share: float, ms: float) -> str:
    if ms < NOISE_MS:
        return "light"
    if share >= HEAVY_SHARE:
        return "heavy"
    if share >= MID_SHARE:
        return "mid"
    return "light"


def median(samples: list) -> float:
    vals = sorted(float(s) for s in samples)
    if not vals:
        return 0.0
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def jitter(samples: list) -> float:
    vals = [float(s) for s in samples]
    return (max(vals) - min(vals)) if vals else 0.0


def overlap_ratio(sum_ms: float, scene_ms: float) -> float:
    if scene_ms <= NOISE_MS or sum_ms <= 0:
        return 1.0
    return sum_ms / scene_ms


def rank(entries: list) -> dict:
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


def measure_row(guid, name, type_label, samples, baseline_s, polygons) -> dict:
    return {
        "guid": guid,
        "name": name,
        "type": type_label,
        "ms": max(0.0, (median(samples) - baseline_s) * 1000.0),
        "jitter_ms": jitter(samples) * 1000.0,
        "runs": len(samples),
        "polygons": int(polygons or 0),
    }


def finish_scan(entries: list, baseline_s: float, scene_ms: float) -> dict:
    result = rank(entries)
    result["ok"] = True
    result["baseline_ms"] = baseline_s * 1000.0
    result["scene_ms"] = scene_ms
    result["summary"]["scene_ms"] = scene_ms
    result["summary"]["overlap"] = overlap_ratio(
        result["summary"]["total_ms"], scene_ms)
    return result
