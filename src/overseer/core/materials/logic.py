from __future__ import annotations


def is_internal_material(name: str) -> bool:
    n = (name or "").strip()
    return len(n) > 4 and n.startswith("__") and n.endswith("__")


def scan_result(total: int, unused: list, only_hidden: list, accepted_out: list,
                accepted_all, missing: list) -> dict:
    return {
        "total": total,
        "unused": unused,
        "only_hidden": only_hidden,
        "accepted": accepted_out,
        "accepted_all": sorted(accepted_all or ()),
        "deletable_count": len(unused),
        "missing": missing[:50],
        "missing_textures": len(missing),
    }
