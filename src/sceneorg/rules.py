"""Declarative, versioned rule engine (pure, no c4d).

Rules live in config.json / presets as a list of dicts discriminated by
`type` and compile into Rule objects that plan RenameOp/ReparentOp/LayerOp
via the existing planners' vocabulary. Unknown rule types are collected as
warnings instead of crashing (forward compatibility: newer presets keep
working on older plugins, minus the unknown rules).

Rule types (RULE_TYPES):
  prefix    contextual prefixes -- e.g. 'LGT_' only for lights under 'Studio'
  renumber  gap renumbering -- 1,2,3,6,7,9 -> 1..6 with padding
  condition declarative if/then -- e.g. 'if >3 duplicates -> alpha suffixes'
  layer     layer assignment by match (extends the fixed DEFAULT_LAYER_SCHEME)
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from . import model, naming, translations
from .convention import NamingConvention
from .ops import LayerOp, RenameOp
from .structure import StructureStandard

RULES_SCHEMA_VERSION = 2

# Separator used between a base name and an appended number/letter suffix,
# mirroring convention._NUM_SEP (kept local: that dict is module-private).
_SUFFIX_SEP = {
    naming.Casing.PASCAL: "",
    naming.Casing.CAMEL: "",
    naming.Casing.LOWER_SNAKE: "_",
    naming.Casing.UPPER_SNAKE: "_",
    naming.Casing.KEBAB: "-",
}


@dataclass
class RuleContext:
    """Everything a rule may inspect while planning."""

    tree: model.SceneTree
    convention: NamingConvention
    standard: StructureStandard
    scope: set | None = None

    def in_scope(self, node: model.SceneNode) -> bool:
        return self.scope is None or node.guid in self.scope


@dataclass
class Match:
    """Shared condition vocabulary for all rule types (extensible).

    categories   object categories, e.g. {'light'}
    keywords     English name tokens (object tokens are translated first)
    name_regex   regex tested against the raw object name
    under_group  group path prefix the object must sit in ('Studio',
                 'Room/Furniture'); resolved via the structure standard
    types        C4D type names, e.g. {'Instance'}
    """

    categories: set = field(default_factory=set)
    keywords: set = field(default_factory=set)
    name_regex: str | None = None
    under_group: str | None = None
    types: set = field(default_factory=set)

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
        if self.keywords:
            tokens = {translations.to_english(t) for t in naming.tokenize(node.name)}
            if not (tokens & self.keywords):
                return False
        if self.name_regex:
            try:
                if not re.search(self.name_regex, node.name):
                    return False
            except re.error:
                return False
        if self.under_group:
            enclosing = ctx.standard.enclosing_group_path(node)
            if not StructureStandard.path_complies(enclosing, self.under_group):
                return False
        return True


@dataclass
class PlanBundle:
    """Combined result of RuleSet.plan_all()."""

    renames: list = field(default_factory=list)
    layers: list = field(default_factory=list)
    applied_rules: list = field(default_factory=list)   # rule ids that produced ops
    warnings: list = field(default_factory=list)


def _suffix_sep(convention: NamingConvention) -> str:
    return _SUFFIX_SEP.get(convention.style, "_")


def _reserve_sibling_names(nodes_to_rename: list) -> dict:
    """Names already taken per parent bucket (siblings that are NOT renamed)."""
    by_parent: dict = defaultdict(set)
    renaming_ids = {id(n) for n in nodes_to_rename}
    for n in nodes_to_rename:
        parent = n.parent
        siblings = parent.children if parent is not None else []
        for s in siblings:
            if id(s) not in renaming_ids:
                by_parent[id(parent) if parent else None].add(s.name)
    return by_parent


# -- Rule types --------------------------------------------------------------


@dataclass
class PrefixRule:
    """Contextual prefix: prepend `prefix` to every matching object name.

    Idempotent: names already carrying the prefix are left alone.
    Replaces/extends the flat per-category `prefixes` config of v1.
    """

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
            bundle.renames.append(RenameOp(
                guid=n.guid, old_name=n.name, new_name=self.prefix + n.name))
        return bundle


@dataclass
class RenumberRule:
    """Gap renumbering: reassign trailing numbers as a gapless series.

    Matching numbered siblings that share the same base name form a series;
    the series is renumbered start..n in document order with `pad` zeros
    (1,2,3,6,7,9 -> 01..06). Idempotent: an already-gapless series with the
    right padding yields zero ops. Unnumbered objects are never touched.

    per_parent=True (default) renumbers each sibling series independently;
    False renumbers one scene-wide series per base name.
    """

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
        # series key -> list of (node, base, num, original separator)
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
        reserved = _reserve_sibling_names(renaming_nodes)

        for group in series.values():
            # Document order is walk order (already the case), keep stable.
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
                bundle.renames.append(RenameOp(
                    guid=n.guid, old_name=n.name, new_name=new_name))
        return bundle


@dataclass
class ConditionRule:
    """Declarative if/then rule.

    when (all given conditions must hold; per candidate set):
      duplicates_gt  N  -- names occurring more than N times (per parent)
      match          {...Match...} -- restrict candidates
    then (one action):
      suffix_scheme  'alpha' | 'numeric' -- disambiguate duplicates with
                     A/B/C or 01/02/03 suffixes
      apply_prefix   'PFX_' -- prefix candidates (idempotent)
      assign_layer   'LayerName' -- put candidates on a layer
    """

    id: str
    when: dict
    then: dict
    enabled: bool = True
    priority: int = 0
    type: str = "condition"

    @classmethod
    def from_dict(cls, data: dict) -> ConditionRule:
        return cls(
            id=data.get("id", ""),
            when=dict(data.get("when") or {}),
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
            # duplicate = same name among siblings, counted per parent
            counts: dict = defaultdict(int)
            for n in nodes:
                counts[(id(n.parent) if n.parent else None, n.name)] += 1
            nodes = [n for n in nodes
                     if counts[(id(n.parent) if n.parent else None, n.name)]
                     > int(dup_gt)]
        return nodes

    @staticmethod
    def _alpha(i: int) -> str:
        """0 -> A, 25 -> Z, 26 -> AA (spreadsheet-style)."""
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
            for (_pk, name), members in groups.items():
                if len(members) < 2:
                    continue
                for i, n in enumerate(members):
                    suffix = self._alpha(i) if scheme == "alpha" \
                        else str(i + 1).zfill(2)
                    new_name = name + sep + suffix
                    if new_name != n.name:
                        bundle.renames.append(RenameOp(
                            guid=n.guid, old_name=n.name, new_name=new_name))
            return bundle

        prefix = self.then.get("apply_prefix")
        if prefix:
            for n in nodes:
                if not n.name.startswith(prefix):
                    bundle.renames.append(RenameOp(
                        guid=n.guid, old_name=n.name, new_name=prefix + n.name))
            return bundle

        layer = self.then.get("assign_layer")
        if layer:
            for n in nodes:
                bundle.layers.append(LayerOp(guid=n.guid, name=n.name, layer=layer))
            return bundle

        bundle.warnings.append(
            "condition rule %r: unknown action %r" % (self.id, self.then))
        return bundle


@dataclass
class LayerRule:
    """Assign matching objects to a named layer (type axis, no hierarchy change)."""

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
                bundle.layers.append(LayerOp(guid=n.guid, name=n.name, layer=self.layer))
        return bundle


RULE_TYPES = {
    "prefix": PrefixRule,
    "renumber": RenumberRule,
    "condition": ConditionRule,
    "layer": LayerRule,
}


# -- Rule set ----------------------------------------------------------------


@dataclass
class RuleSet:
    rules: list = field(default_factory=list)
    warnings: list = field(default_factory=list)   # from compilation

    def to_list(self) -> list:
        return [r.to_dict() for r in self.rules]

    def plan_all(self, ctx: RuleContext) -> PlanBundle:
        """Run all enabled rules (priority descending) and merge their ops.

        Later rules never re-rename an object an earlier rule already
        claimed (first claim wins -- deterministic, no op chains on stale
        names). Layer ops: last assignment per object wins is avoided the
        same way (first claim wins).
        """
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
    """list[dict] -> RuleSet. Unknown/invalid rules become warnings."""
    ruleset = RuleSet()
    for i, item in enumerate(raw or []):
        rtype = (item or {}).get("type")
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
