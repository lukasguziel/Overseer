"""Externe Konfiguration (config.json) -> Konvention/Standard/Praefixe (rein).

Der Dialog liest die JSON-Datei und ruft `load_config(dict)`. Dieses Modul
selbst hat KEINE Seiteneffekte (leicht testbar).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .convention import NamingConvention
from .naming import Casing
from .structure import GroupRule, StructureStandard, default_standard

DEFAULT_CONFIG = {
    "casing": "PascalCase",        # PascalCase | camelCase | lower_snake | UPPER_SNAKE | kebab
    "language": "en",              # en | de | null (keine Uebersetzung)
    "number_pad": 2,               # 0 | 2 | 3
    "prefixes": {},                # {"light": "LGT_", "camera": "CAM_", "mesh": "GEO_"}
    "groups": None,                # optionale Ueberschreibung der Struktur-Regeln
    "translations": {},            # zusaetzliche de->en Paare
}


@dataclass
class Config:
    convention: NamingConvention
    standard: StructureStandard
    prefixes: dict = field(default_factory=dict)
    extra_translations: dict = field(default_factory=dict)


def build_convention(data: dict) -> NamingConvention:
    casing = Casing(data.get("casing") or "PascalCase")
    language = data.get("language", "en")   # kann None sein
    pad = int(data.get("number_pad", 2))
    return NamingConvention(style=casing, language=language, number_pad=pad)


def build_standard(data: dict) -> StructureStandard:
    groups = data.get("groups")
    if not groups:
        return default_standard()
    rules = []
    for g in groups:
        rules.append(GroupRule(
            name=g["name"],
            match_categories=set(g.get("categories", [])),
            match_keywords={k.lower() for k in g.get("keywords", [])},
            aliases={a.lower() for a in g.get("aliases", [])},
            priority=int(g.get("priority", 0)),
        ))
    return StructureStandard(rules)


def load_config(data: dict | None = None) -> Config:
    merged = dict(DEFAULT_CONFIG)
    if data:
        merged.update(data)
    return Config(
        convention=build_convention(merged),
        standard=build_standard(merged),
        prefixes=dict(merged.get("prefixes") or {}),
        extra_translations=dict(merged.get("translations") or {}),
    )
