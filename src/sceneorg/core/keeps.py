"""Per-section "accepted as-is" lists (pure, no c4d).

Each suggestion area keeps a list of keys the user accepted as-is; those
items are filtered out of plans server-side and never counted as todos.
Keys are names (not GUIDs) so they survive across sessions.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

SECTIONS = ("naming", "translate", "layers", "structure", "materials")


def empty_keeps() -> dict:
    return {s: [] for s in SECTIONS}


def normalize_keeps(raw: dict | None) -> dict:
    """Coerce a config `keeps` value into a full, sorted, deduped map."""
    out = empty_keeps()
    for section, keys in (raw or {}).items():
        if section in out:
            out[section] = sorted({str(k) for k in (keys or [])})
    return out


def set_section_keeps(keeps: dict | None, section: str, keys: Iterable) -> dict:
    """Return a new keeps map with `section` replaced by `keys`."""
    if section not in SECTIONS:
        raise ValueError(f"unknown keeps section: {section!r}")
    out = normalize_keeps(keeps)
    out[section] = sorted({str(k) for k in (keys or [])})
    return out


def filter_kept(items: list, kept: set, key: Callable) -> tuple[list, list]:
    """Split plan items into (todo, kept_keys) by key(item) membership."""
    todo: list = []
    hits: list = []
    for item in items:
        k = key(item)
        if k in kept:
            hits.append(k)
        else:
            todo.append(item)
    return todo, sorted(set(hits))
