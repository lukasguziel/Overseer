from __future__ import annotations


def is_internal_material(name: str) -> bool:
    n = (name or "").strip()
    return len(n) > 4 and n.startswith("__") and n.endswith("__")
