from __future__ import annotations

from collections.abc import Callable, Iterable

SECTIONS = ("naming", "translate", "layers", "structure", "materials", "files", "textures")


def empty_keeps() -> dict:
    return {s: [] for s in SECTIONS}


def normalize_keeps(raw: dict | None) -> dict:
    out = empty_keeps()
    for section, keys in (raw or {}).items():
        if section in out:
            out[section] = sorted({str(k) for k in (keys or [])})
    return out


def set_section_keeps(keeps: dict | None, section: str, keys: Iterable) -> dict:
    if section not in SECTIONS:
        raise ValueError(f"unknown keeps section: {section!r}")
    out = normalize_keeps(keeps)
    out[section] = sorted({str(k) for k in (keys or [])})
    return out


def filter_kept(items: list, kept: set, key: Callable) -> tuple[list, list]:
    todo: list = []
    hits: list = []
    for item in items:
        k = key(item)
        if k in kept:
            hits.append(k)
        else:
            todo.append(item)
    return todo, sorted(set(hits))
