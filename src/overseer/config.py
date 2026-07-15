from __future__ import annotations

from dataclasses import dataclass, field

from .core.keeps import empty_keeps, normalize_keeps
from .naming.casing import Casing
from .naming.convention import NamingConvention
from .structure.rules import RuleSet, compile_rules
from .structure.standard import GroupRule, StructureStandard, default_standard

CONFIG_SCHEMA_VERSION = 3

_MIGRATED_PREFIX_ID = "prefix_%s_v1"

DEFAULT_CONFIG = {
    "schema": CONFIG_SCHEMA_VERSION,
    "casing": "PascalCase",
    "language": "en",
    "number_pad": 2,
    "structure": None,
    "rules": [],
    "translations": {},
    "keeps": empty_keeps(),
}


@dataclass
class Config:
    convention: NamingConvention
    standard: StructureStandard
    rules: RuleSet
    prefixes: dict = field(default_factory=dict)
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
    schema = _as_int(out.get("schema") or 1, 1)
    if schema >= CONFIG_SCHEMA_VERSION:
        out["schema"] = CONFIG_SCHEMA_VERSION
        out["keeps"] = normalize_keeps(out.get("keeps"))
        return out

    if schema < 2:
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


def _collect_group_rules(nodes: list, parent: str | None, rules: list) -> None:
    for g in nodes or []:
        if not isinstance(g, dict):
            continue

        rule = GroupRule(
            name=str(g.get("name") or "Group"),
            match_categories=set(g.get("categories") or []),
            match_keywords={str(k).lower() for k in (g.get("keywords") or [])},
            aliases={str(a).lower() for a in (g.get("aliases") or [])},
            priority=_as_int(g.get("priority", 0), 0),
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
        keeps=normalize_keeps(merged.get("keeps")),
    )
