from __future__ import annotations

from dataclasses import dataclass, field

from .core.naming.casing import Casing
from .core.naming.convention import NamingConvention
from .core.organize.keeps import empty_keeps, normalize_keeps

CONFIG_SCHEMA_VERSION = 3

DEFAULT_CONFIG = {
    "schema": CONFIG_SCHEMA_VERSION,
    "casing": "PascalCase",
    "language": "en",
    "number_pad": 2,
    "translations": {},
    "keeps": empty_keeps(),
    "listen_lan": False,
}

MACHINE_LOCAL_KEYS = ("port", "listen_lan")

_RETIRED_KEYS = ("structure", "rules", "graph", "preset", "prefixes", "groups")


@dataclass
class Config:
    convention: NamingConvention
    extra_translations: dict = field(default_factory=dict)
    keeps: dict = field(default_factory=dict)

    def kept(self, section: str) -> set:
        return {str(n) for n in (self.keeps.get(section) or [])}

    @property
    def keep_names(self) -> set:
        return self.kept("naming")

    @property
    def accepted_unused(self) -> set:
        return self.kept("materials")


def _as_int(value: object, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def migrate_config(data: dict) -> dict:
    out = dict(data or {})
    for key in _RETIRED_KEYS:
        out.pop(key, None)

    keeps = normalize_keeps(out.get("keeps"))
    if out.get("keep_names"):
        keeps["naming"] = sorted({str(n) for n in out["keep_names"]} | set(keeps["naming"]))
    if out.get("accepted_unused"):
        keeps["materials"] = sorted({str(n) for n in out["accepted_unused"]} | set(keeps["materials"]))
    out.pop("keep_names", None)
    out.pop("accepted_unused", None)
    out["keeps"] = keeps
    out["schema"] = CONFIG_SCHEMA_VERSION
    return out


def build_convention(data: dict) -> NamingConvention:
    try:
        casing = Casing(data.get("casing") or DEFAULT_CONFIG["casing"])
    except ValueError:
        casing = Casing(DEFAULT_CONFIG["casing"])
    language = data.get("language", DEFAULT_CONFIG["language"])
    pad = _as_int(data.get("number_pad", 2), 2)
    keep_separators = bool(data.get("keep_separators", False))
    return NamingConvention(style=casing, language=language, number_pad=pad,
                            keep_separators=keep_separators)


def load_config(data: dict | None = None) -> Config:
    merged = dict(DEFAULT_CONFIG)
    if data:
        merged.update(migrate_config(data))
    return Config(
        convention=build_convention(merged),
        extra_translations=dict(merged.get("translations") or {}),
        keeps=normalize_keeps(merged.get("keeps")),
    )
