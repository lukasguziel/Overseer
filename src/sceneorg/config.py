from __future__ import annotations

from dataclasses import dataclass, field

from .naming.casing import Casing
from .naming.convention import NamingConvention
from .structure.rules import RuleSet, compile_rules
from .structure.standard import GroupRule, StructureStandard, default_standard

CONFIG_SCHEMA_VERSION = 2

_MIGRATED_PREFIX_ID = "prefix_%s_v1"

DEFAULT_CONFIG = {
    "schema": CONFIG_SCHEMA_VERSION,
    "casing": "PascalCase",
    "language": "en",
    "number_pad": 2,
    "structure": None,
    "rules": [],
    "translations": {},
}


@dataclass
class Config:
    convention: NamingConvention
    standard: StructureStandard
    rules: RuleSet
    prefixes: dict = field(default_factory=dict)
    extra_translations: dict = field(default_factory=dict)


def migrate_config(data: dict) -> dict:
    out = dict(data or {})
    if int(out.get("schema") or 1) >= CONFIG_SCHEMA_VERSION:
        out["schema"] = CONFIG_SCHEMA_VERSION
        return out

    out["schema"] = CONFIG_SCHEMA_VERSION
    rules = list(out.get("rules") or [])
    for cat, prefix in (out.pop("prefixes", None) or {}).items():
        rules.append({
            "id": _MIGRATED_PREFIX_ID % cat,
            "type": "prefix",
            "prefix": prefix,
            "match": {"categories": [cat]},
        })
    out["rules"] = rules

    groups = out.pop("groups", None)
    if groups:
        out["structure"] = [dict(g) for g in groups]
    else:
        out.setdefault("structure", None)
    return out


def build_convention(data: dict) -> NamingConvention:
    casing = Casing(data.get("casing") or "PascalCase")
    language = data.get("language", "en")
    pad = int(data.get("number_pad", 2))
    return NamingConvention(style=casing, language=language, number_pad=pad)


def _collect_group_rules(nodes: list, parent: str | None, rules: list) -> None:
    for g in nodes or []:
        rule = GroupRule(
            name=g["name"],
            match_categories=set(g.get("categories", [])),
            match_keywords={k.lower() for k in g.get("keywords", [])},
            aliases={a.lower() for a in g.get("aliases", [])},
            priority=int(g.get("priority", 0)),
            parent=parent,
        )
        rules.append(rule)
        _collect_group_rules(g.get("children"), rule.path, rules)


def build_standard(data: dict) -> StructureStandard:
    structure = data.get("structure")
    if not structure:
        return default_standard()
    rules: list = []
    _collect_group_rules(structure, None, rules)
    return StructureStandard(rules)


def structure_to_list(standard: StructureStandard) -> list:
    by_path: dict = {}
    roots: list = []

    for rule in sorted(standard.rules, key=lambda r: r.path.count("/")):
        entry: dict = {"name": rule.name}
        if rule.match_categories:
            entry["categories"] = sorted(rule.match_categories)
        if rule.match_keywords:
            entry["keywords"] = sorted(rule.match_keywords)
        if rule.aliases:
            entry["aliases"] = sorted(rule.aliases)
        if rule.priority:
            entry["priority"] = rule.priority
        by_path[rule.path] = entry
        if rule.parent and rule.parent in by_path:
            by_path[rule.parent].setdefault("children", []).append(entry)
        else:
            roots.append(entry)
    return roots


def _legacy_prefixes(ruleset: RuleSet) -> dict:
    out: dict = {}
    for r in ruleset.rules:
        if r.type != "prefix" or not r.enabled:
            continue
        m = r.match
        if (len(m.categories) == 1 and not m.keywords and not m.name_regex
                and not m.under_group and not m.types):
            out[next(iter(m.categories))] = r.prefix
    return out


def load_config(data: dict | None = None) -> Config:
    merged = dict(DEFAULT_CONFIG)
    if data:
        merged.update(migrate_config(data))
    ruleset = compile_rules(merged.get("rules"))
    return Config(
        convention=build_convention(merged),
        standard=build_standard(merged),
        rules=ruleset,
        prefixes=_legacy_prefixes(ruleset),
        extra_translations=dict(merged.get("translations") or {}),
    )
