from __future__ import annotations


def normalize_entry(entry: dict) -> dict:
    items = entry.get("items") or []
    for it in items:
        if "reverted" not in it:
            it["reverted"] = False
    entry["items"] = items
    entry.setdefault("reverted", False)
    entry.setdefault("revertible", bool(items))
    return entry


def normalize_journal(entries: list | None) -> list:
    out = [normalize_entry(dict(e)) for e in (entries or []) if isinstance(e, dict)]
    out.sort(key=lambda e: e.get("ts", 0))
    return out


def merge_journals(a: list | None, b: list | None) -> list:
    by_id: dict = {}
    for e in normalize_journal(a) + normalize_journal(b):
        eid = str(e.get("id", ""))
        prev = by_id.get(eid)
        if prev is None or e.get("ts", 0) >= prev.get("ts", 0):
            by_id[eid] = e
    return sorted(by_id.values(), key=lambda e: e.get("ts", 0))


def items_to_revert(entry: dict, indices: list | None = None) -> list:
    items = entry.get("items") or []
    if indices is None:
        chosen = range(len(items))
    else:
        chosen = [i for i in indices if isinstance(i, int) and 0 <= i < len(items)]
    return [(i, items[i]) for i in chosen if not items[i].get("reverted")]


def mark_reverted(entry: dict, indices: list) -> dict:
    items = entry.get("items") or []
    for i in indices:
        if isinstance(i, int) and 0 <= i < len(items):
            items[i]["reverted"] = True
    if items and all(it.get("reverted") for it in items):
        entry["reverted"] = True
    return entry


def set_entry(entries: list, entry: dict) -> list:
    eid = str(entry.get("id", ""))
    for idx, e in enumerate(entries):
        if str(e.get("id", "")) == eid:
            entries[idx] = entry
            break
    return entries


def change_item(sid, name, field, before, after) -> dict:
    return {"sid": sid, "name": name, "field": field,
            "before": before, "after": after}
