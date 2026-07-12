from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field

from ..core import model
from ..core.ops import LayerOp, RenameOp
from ..naming import casing as naming
from ..naming.convention import NamingConvention
from .standard import StructureStandard, english_tokens

RULES_SCHEMA_VERSION = 2

_SUFFIX_SEP = {
    naming.Casing.PASCAL: "",
    naming.Casing.CAMEL: "",
    naming.Casing.LOWER_SNAKE: "_",
    naming.Casing.UPPER_SNAKE: "_",
    naming.Casing.KEBAB: "-",
}


@dataclass
class RuleContext:
    tree: model.SceneTree
    convention: NamingConvention
    standard: StructureStandard
    scope: set | None = None
    token_cache: dict = field(default_factory=dict, repr=False, compare=False)
    group_cache: dict = field(default_factory=dict, repr=False, compare=False)

    def in_scope(self, node: model.SceneNode) -> bool:
        return self.scope is None or node.guid in self.scope

    def tokens(self, node: model.SceneNode) -> set:
        hit = self.token_cache.get(node.name)
        if hit is None:
            hit = english_tokens(node.name)
            self.token_cache[node.name] = hit
        return hit

    def enclosing_group_path(self, node: model.SceneNode) -> str | None:
        key = id(node)
        if key not in self.group_cache:
            self.group_cache[key] = self.standard.enclosing_group_path(node)
        return self.group_cache[key]


@dataclass
class Match:
    categories: set = field(default_factory=set)
    keywords: set = field(default_factory=set)
    name_regex: str | None = None
    under_group: str | None = None
    types: set = field(default_factory=set)
    pattern: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.name_regex:
            self.pattern = None
            return

        try:
            self.pattern = re.compile(self.name_regex)
        except re.error as exc:
            raise ValueError(
                "invalid name_regex %r: %s" % (self.name_regex, exc)) from exc

    @classmethod
    def from_dict(cls, data: dict | None) -> Match:
        data = data or {}
        return cls(
            categories=set(data.get("categories", [])),
            keywords={k.lower() for k in data.get("keywords", [])},
            name_regex=data.get("name_regex"),
            under_group=data.get("under_group"),
            types=set(data.get("types", [])),
        )

    def to_dict(self) -> dict:
        out: dict = {}
        if self.categories:
            out["categories"] = sorted(self.categories)
        if self.keywords:
            out["keywords"] = sorted(self.keywords)
        if self.name_regex:
            out["name_regex"] = self.name_regex
        if self.under_group:
            out["under_group"] = self.under_group
        if self.types:
            out["types"] = sorted(self.types)
        return out

    def matches(self, node: model.SceneNode, ctx: RuleContext) -> bool:
        if self.categories and node.category not in self.categories:
            return False
        if self.types and node.type_name not in self.types:
            return False
        if self.keywords and not (ctx.tokens(node) & self.keywords):
            return False
        if self.pattern is not None and not self.pattern.search(node.name):
            return False
        if self.under_group:
            enclosing = ctx.enclosing_group_path(node)
            if not StructureStandard.path_complies(enclosing, self.under_group):
                return False
        return True


@dataclass
class PlanBundle:
    renames: list = field(default_factory=list)
    layers: list = field(default_factory=list)
    applied_rules: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


class Rule(ABC):
    id: str
    enabled: bool
    priority: int
    type: str

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict) -> Rule: ...

    @abstractmethod
    def to_dict(self) -> dict: ...

    @abstractmethod
    def plan(self, ctx: RuleContext) -> PlanBundle: ...


def _suffix_sep(convention: NamingConvention) -> str:
    return _SUFFIX_SEP.get(convention.style, "_")


def _reserve_sibling_names(nodes_to_rename: list, roots: list) -> dict:
    by_parent: dict = defaultdict(set)
    renaming_ids = {id(n) for n in nodes_to_rename}
    for n in nodes_to_rename:
        parent = n.parent
        siblings = parent.children if parent is not None else roots
        for s in siblings:
            if id(s) not in renaming_ids:
                by_parent[id(parent) if parent else None].add(s.name)
    return by_parent


@dataclass
class PrefixRule(Rule):
    id: str
    prefix: str
    match: Match
    enabled: bool = True
    priority: int = 0
    type: str = "prefix"

    @classmethod
    def from_dict(cls, data: dict) -> PrefixRule:
        return cls(
            id=data.get("id", ""),
            prefix=data["prefix"],
            match=Match.from_dict(data.get("match")),
            enabled=bool(data.get("enabled", True)),
            priority=int(data.get("priority", 0)),
        )

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "prefix": self.prefix,
                "match": self.match.to_dict(), "enabled": self.enabled,
                "priority": self.priority}

    def plan(self, ctx: RuleContext) -> PlanBundle:
        bundle = PlanBundle()
        for n in ctx.tree.walk():
            if not ctx.in_scope(n) or not self.match.matches(n, ctx):
                continue
            if n.name.startswith(self.prefix):
                continue
            bundle.renames.append(RenameOp(node=n, new_name=self.prefix + n.name))
        return bundle


@dataclass
class RenumberRule(Rule):
    id: str
    match: Match
    pad: int = 2
    start: int = 1
    per_parent: bool = True
    enabled: bool = True
    priority: int = 0
    type: str = "renumber"

    @classmethod
    def from_dict(cls, data: dict) -> RenumberRule:
        return cls(
            id=data.get("id", ""),
            match=Match.from_dict(data.get("match")),
            pad=int(data.get("pad", 2)),
            start=int(data.get("start", 1)),
            per_parent=bool(data.get("per_parent", True)),
            enabled=bool(data.get("enabled", True)),
            priority=int(data.get("priority", 0)),
        )

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "match": self.match.to_dict(),
                "pad": self.pad, "start": self.start,
                "per_parent": self.per_parent, "enabled": self.enabled,
                "priority": self.priority}

    def _format(self, num: int) -> str:
        return str(num).zfill(self.pad) if self.pad > 0 else str(num)

    def plan(self, ctx: RuleContext) -> PlanBundle:
        bundle = PlanBundle()
        sep = _suffix_sep(ctx.convention)

        series: dict = defaultdict(list)
        for n in ctx.tree.walk():
            if not ctx.in_scope(n) or not self.match.matches(n, ctx):
                continue
            base, num = naming.split_trailing_number(n.name)
            if num is None or not base:
                continue
            parent_key = id(n.parent) if self.per_parent else None
            series[(parent_key, base.lower())].append((n, base, num))

        renaming_nodes = [n for group in series.values() for (n, _, _) in group]
        reserved = _reserve_sibling_names(renaming_nodes, ctx.tree.roots)

        for group in series.values():
            group.sort(key=lambda t: t[2])
            for i, (n, base, _num) in enumerate(group):
                new_name = base + sep + self._format(self.start + i)
                if new_name == n.name:
                    continue
                parent_key = id(n.parent) if n.parent else None
                if new_name in reserved.get(parent_key, set()):
                    bundle.warnings.append(
                        "renumber %r: target %r taken by a sibling, skipped"
                        % (n.name, new_name))
                    continue
                bundle.renames.append(RenameOp(node=n, new_name=new_name))
        return bundle


@dataclass
class ConditionRule(Rule):
    id: str
    when: dict
    then: dict
    enabled: bool = True
    priority: int = 0
    type: str = "condition"

    @classmethod
    def from_dict(cls, data: dict) -> ConditionRule:
        when = dict(data.get("when") or {})
        Match.from_dict(when.get("match"))

        return cls(
            id=data.get("id", ""),
            when=when,
            then=dict(data.get("then") or {}),
            enabled=bool(data.get("enabled", True)),
            priority=int(data.get("priority", 0)),
        )

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "when": self.when,
                "then": self.then, "enabled": self.enabled,
                "priority": self.priority}

    def _candidates(self, ctx: RuleContext) -> list:
        match = Match.from_dict(self.when.get("match"))
        nodes = [n for n in ctx.tree.walk()
                 if ctx.in_scope(n) and match.matches(n, ctx)]
        dup_gt = self.when.get("duplicates_gt")
        if dup_gt is not None:
            counts: dict = defaultdict(int)
            for n in nodes:
                counts[(id(n.parent) if n.parent else None, n.name)] += 1
            nodes = [n for n in nodes
                     if counts[(id(n.parent) if n.parent else None, n.name)]
                     > int(dup_gt)]
        return nodes

    @classmethod
    def _suffix(cls, scheme: str, i: int, pad: int) -> str:
        if scheme == "alpha":
            return cls._alpha(i)
        return str(i + 1).zfill(pad)

    @staticmethod
    def _alpha(i: int) -> str:
        out = ""
        i += 1
        while i > 0:
            i, rem = divmod(i - 1, 26)
            out = chr(ord("A") + rem) + out
        return out

    def plan(self, ctx: RuleContext) -> PlanBundle:
        bundle = PlanBundle()
        nodes = self._candidates(ctx)
        if not nodes:
            return bundle
        sep = _suffix_sep(ctx.convention)

        scheme = self.then.get("suffix_scheme")
        if scheme in ("alpha", "numeric"):
            groups: dict = defaultdict(list)
            for n in nodes:
                groups[(id(n.parent) if n.parent else None, n.name)].append(n)

            renaming = [n for members in groups.values() if len(members) > 1
                        for n in members]
            reserved = _reserve_sibling_names(renaming, ctx.tree.roots)
            pad = max(int(ctx.convention.number_pad), 0)

            for (pk, name), members in groups.items():
                if len(members) < 2:
                    continue
                taken = reserved.get(pk, set())
                i = 0
                for n in members:
                    new_name = name + sep + self._suffix(scheme, i, pad)
                    while new_name in taken:
                        i += 1
                        new_name = name + sep + self._suffix(scheme, i, pad)
                    i += 1
                    if new_name != n.name:
                        bundle.renames.append(RenameOp(node=n, new_name=new_name))
            return bundle

        prefix = self.then.get("apply_prefix")
        if prefix:
            for n in nodes:
                if not n.name.startswith(prefix):
                    bundle.renames.append(RenameOp(node=n, new_name=prefix + n.name))
            return bundle

        layer = self.then.get("assign_layer")
        if layer:
            for n in nodes:
                bundle.layers.append(LayerOp(node=n, layer=layer))
            return bundle

        bundle.warnings.append(
            "condition rule %r: unknown action %r" % (self.id, self.then))
        return bundle


@dataclass
class LayerRule(Rule):
    id: str
    layer: str
    match: Match
    enabled: bool = True
    priority: int = 0
    type: str = "layer"

    @classmethod
    def from_dict(cls, data: dict) -> LayerRule:
        return cls(
            id=data.get("id", ""),
            layer=data["layer"],
            match=Match.from_dict(data.get("match")),
            enabled=bool(data.get("enabled", True)),
            priority=int(data.get("priority", 0)),
        )

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "layer": self.layer,
                "match": self.match.to_dict(), "enabled": self.enabled,
                "priority": self.priority}

    def plan(self, ctx: RuleContext) -> PlanBundle:
        bundle = PlanBundle()
        for n in ctx.tree.walk():
            if ctx.in_scope(n) and self.match.matches(n, ctx):
                bundle.layers.append(LayerOp(node=n, layer=self.layer))
        return bundle


RULE_TYPES = {
    "prefix": PrefixRule,
    "renumber": RenumberRule,
    "condition": ConditionRule,
    "layer": LayerRule,
}


@dataclass
class RuleSet:
    rules: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_list(self) -> list:
        return [r.to_dict() for r in self.rules]

    def plan_all(self, ctx: RuleContext) -> PlanBundle:
        bundle = PlanBundle(warnings=list(self.warnings))
        renamed: set = set()
        layered: set = set()
        for rule in sorted(self.rules, key=lambda r: -r.priority):
            if not rule.enabled:
                continue
            part = rule.plan(ctx)
            produced = False
            for op in part.renames:
                if op.guid not in renamed:
                    renamed.add(op.guid)
                    bundle.renames.append(op)
                    produced = True
            for op in part.layers:
                if op.guid not in layered:
                    layered.add(op.guid)
                    bundle.layers.append(op)
                    produced = True
            bundle.warnings.extend(part.warnings)
            if produced and rule.id:
                bundle.applied_rules.append(rule.id)
        return bundle


def compile_rules(raw: list | None) -> RuleSet:
    ruleset = RuleSet()
    for i, item in enumerate(raw or []):
        if not isinstance(item, dict):
            ruleset.warnings.append(
                "rule #%d is not an object (%r) -- skipped" % (i, item))
            continue

        rtype = item.get("type")
        cls = RULE_TYPES.get(rtype)
        if cls is None:
            ruleset.warnings.append("unknown rule type %r (rule #%d) -- skipped"
                                    % (rtype, i))
            continue
        try:
            rule = cls.from_dict(item)
        except (KeyError, TypeError, ValueError) as exc:
            ruleset.warnings.append("invalid %r rule #%d: %s" % (rtype, i, exc))
            continue
        if not rule.id:
            rule.id = "%s_%d" % (rtype, i + 1)
        ruleset.rules.append(rule)
    return ruleset
