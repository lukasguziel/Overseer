from __future__ import annotations

import hashlib

PERSISTED_KEYS = {
    "casing": str,
    "applyCasing": bool,
    "keepSeparators": bool,
    "keepSpecials": bool,
    "language": str,
    "numberPad": int,
    "applyNumbering": bool,
    "dedupe": bool,
    "safe": bool,
    "tidy": bool,
    "translateTarget": str,
    "translateEngine": str,
    "includeHidden": bool,
}


def _slug_text(text: str) -> str:
    out: list = []
    for ch in text.strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")


def project_slug(path: str, name: str) -> str:
    p = (path or "").strip()
    n = (name or "").strip()
    if not p and not n:
        return ""
    base = _slug_text(n) or _slug_text(p) or "project"
    identity = p + "\x00" + n
    digest = hashlib.sha1(identity.encode("utf-8")).hexdigest()[:8]
    return "%s-%s" % (base, digest)


def sanitize_global_ui(raw: object) -> dict:
    """The GLOBAL ui profile (one file for all projects), currently the area
    profile: which tool areas the web UI hides from its menu (hidden areas
    also stop counting toward the health score). Kept separate from the
    per-project keys — hiding the Tags tool is a "how I work" choice, not a
    property of one scene."""
    if not isinstance(raw, dict):
        return {}
    out: dict = {}
    hidden = raw.get("hiddenAreas")
    if isinstance(hidden, list):
        seen: set = set()
        uniq: list = []
        for v in hidden:
            if isinstance(v, str) and v and v not in seen:
                seen.add(v)
                uniq.append(v)
        out["hiddenAreas"] = uniq[:32]
    return out


def sanitize_ui(raw: object) -> dict:
    if not isinstance(raw, dict):
        return {}
    out: dict = {}
    for key, typ in PERSISTED_KEYS.items():
        if key not in raw:
            continue
        val = raw[key]
        if typ is bool:
            if isinstance(val, bool):
                out[key] = val
        elif typ is int:
            if isinstance(val, bool):
                continue
            if isinstance(val, int):
                out[key] = val
            elif isinstance(val, float) and val.is_integer():
                out[key] = int(val)
        elif typ is str:
            if isinstance(val, str):
                out[key] = val
    return out
