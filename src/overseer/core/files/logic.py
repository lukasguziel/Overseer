from __future__ import annotations

import os

IMAGE_EXTS = frozenset({
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".hdr", ".tga",
    ".psd", ".bmp", ".gif", ".iff", ".dds", ".webp", ".pict", ".pct",
    ".rla", ".rpf", ".dpx", ".sgi", ".rgb", ".b3d", ".tx",
})

_KIND_EXTS = {
    ".abc": "alembic",
    ".c4d": "scene",
    ".mog": "cache",
    ".vdb": "cache",
    ".bgeo": "cache",
    ".prt": "cache",
    ".ies": "ies",
    ".wav": "audio",
    ".mp3": "audio",
    ".aif": "audio",
    ".aiff": "audio",
    ".flac": "audio",
    ".m4a": "audio",
    ".ogg": "audio",
    ".mp4": "video",
    ".mov": "video",
    ".avi": "video",
    ".mkv": "video",
    ".mxf": "video",
}


def file_ext(path: str) -> str:
    return os.path.splitext(str(path or ""))[1].lower()


def is_image(path: str) -> bool:
    return file_ext(path) in IMAGE_EXTS


def classify_kind(path: str) -> str:
    return _KIND_EXTS.get(file_ext(path), "other")


def relocatable(raw: str, resolved: str, exists: bool, doc_path: str) -> tuple[bool, str]:
    if not (os.path.isabs(raw) and exists and doc_path):
        return False, ""
    try:
        rp = os.path.relpath(resolved, doc_path)
    except Exception:
        return False, ""
    if rp.startswith(".."):
        return False, ""
    return True, rp.replace("\\", "/")


def summarize(entries: list) -> dict:
    by_kind: dict = {}
    total_bytes = 0
    missing = absolute = reloc = 0
    for e in entries:
        by_kind[e["kind"]] = by_kind.get(e["kind"], 0) + 1
        total_bytes += e.get("bytes", 0) or 0
        if e.get("missing"):
            missing += 1
        if e.get("absolute"):
            absolute += 1
        if e.get("relocatable"):
            reloc += 1
    return {
        "total": len(entries),
        "by_kind": by_kind,
        "missing_count": missing,
        "absolute_count": absolute,
        "relocatable_count": reloc,
        "total_bytes": total_bytes,
    }


def file_entry(kind: str, raw: str, resolved: str, exists: bool,
               absolute: bool, reloc: bool, rel_target: str, disk_bytes: int,
               owner: str, guid, owner_kind: str = "") -> dict:
    return {
        "kind": kind,
        "file": os.path.basename(raw),
        "path": raw,
        "resolved": resolved,
        "exists": exists,
        "missing": not exists,
        "absolute": absolute,
        "relocatable": reloc,
        "rel_target": rel_target,
        "bytes": disk_bytes,
        "owner": owner,
        "guid": guid,
        "owner_kind": owner_kind,
    }


def scan_result(entries: list, doc_path: str, kept) -> dict:
    kept = set(kept or ())
    accepted = sorted({e["path"] for e in entries
                       if e["missing"] and e["path"] in kept})
    entries = [e for e in entries
               if not (e["missing"] and e["path"] in kept)]
    entries.sort(key=lambda e: e["bytes"], reverse=True)
    return {"ok": True, "doc_path": doc_path, "entries": entries,
            "accepted": accepted, "accepted_all": sorted(kept),
            "summary": summarize(entries)}
