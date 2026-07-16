from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field

from ..naming.convention import NamingConvention
from . import model
from .defaults import DEFAULT_LAYER_SCHEME


class Writer(ABC):
    @abstractmethod
    def rename(self, node: model.SceneNode, new_name: str) -> None: ...

    @abstractmethod
    def reparent(self, node: model.SceneNode, to_group: str) -> None: ...

    @abstractmethod
    def assign_layer(self, node: model.SceneNode, layer: str) -> None: ...


class Operation(ABC):
    node: model.SceneNode

    @property
    def guid(self) -> int:
        return self.node.guid

    @property
    def name(self) -> str:
        return self.node.name

    @abstractmethod
    def apply(self, writer: Writer) -> None: ...

    @abstractmethod
    def to_dict(self) -> dict: ...


@dataclass
class RenameOp(Operation):
    node: model.SceneNode = field(compare=False)
    new_name: str = ""
    rules: list = field(default_factory=lambda: ["casing"])

    @property
    def old_name(self) -> str:
        return self.node.name

    def apply(self, writer: Writer) -> None:
        writer.rename(self.node, self.new_name)

    def to_dict(self) -> dict:
        return {"guid": self.guid, "old": self.old_name, "new": self.new_name,
                "rules": self.rules}


@dataclass
class ReparentOp(Operation):
    node: model.SceneNode = field(compare=False)
    to_group: str = ""
    from_group: str = ""

    def apply(self, writer: Writer) -> None:
        writer.reparent(self.node, self.to_group)

    def to_dict(self) -> dict:
        return {"guid": self.guid, "name": self.name,
                "from": self.from_group, "to": self.to_group}


@dataclass
class LayerOp(Operation):
    node: model.SceneNode = field(compare=False)
    layer: str = ""

    def apply(self, writer: Writer) -> None:
        writer.assign_layer(self.node, self.layer)

    def to_dict(self) -> dict:
        return {"guid": self.guid, "name": self.name, "layer": self.layer}


def layer_for(node: model.SceneNode, scheme: dict | None = None) -> str | None:
    scheme = scheme or DEFAULT_LAYER_SCHEME
    by_type = scheme.get("types", {})
    if node.type_name in by_type:
        return by_type[node.type_name]
    return scheme.get("categories", {}).get(node.category)


def _rename_rules(convention: NamingConvention, raw: str,
                  orig: str, base: str, final: str) -> list[str]:
    prev = convention.apply_numbering
    convention.apply_numbering = False
    try:
        casing_only = convention.normalize(raw)
    finally:
        convention.apply_numbering = prev

    rules: list[str] = []
    if casing_only != orig:
        rules.append("casing")
    if convention.apply_numbering and base != casing_only:
        rules.append("numbering")
    if final != base:
        rules.append("unique")
    return rules or ["casing"]


def plan_renames(
    tree: model.SceneTree,
    convention: NamingConvention,
    scope: set | None = None,
    keep: set | None = None,
    dedupe: bool = True,
) -> list[RenameOp]:
    keep = keep or set()
    buckets: dict = defaultdict(list)
    for n in tree.walk():
        key = id(n.parent) if n.parent is not None else None
        buckets[key].append(n)

    ops: list[RenameOp] = []
    for children in buckets.values():
        used: set = set()
        renaming = []
        for c in children:
            if c.name in keep:
                used.add(c.name)
            elif scope is None or c.guid in scope:
                renaming.append(c)
            else:
                used.add(c.name)

        for c in renaming:
            raw = c.name
            base = convention.normalize(raw)
            if not base:
                used.add(c.name)
                continue

            final = base
            if dedupe:
                i = 1
                while final in used:
                    final = convention.disambiguate(base, i)
                    i += 1
            used.add(final)
            if final != c.name:
                rules = _rename_rules(convention, raw, c.name, base, final)
                ops.append(RenameOp(node=c, new_name=final, rules=rules))
    return ops


def plan_layers(
    tree: model.SceneTree,
    scope: set | None = None,
    scheme: dict | None = None,
) -> list[LayerOp]:
    ops: list[LayerOp] = []
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        layer = layer_for(n, scheme)
        if layer and getattr(n, "layer", None) != layer:
            ops.append(LayerOp(node=n, layer=layer))
    return ops


def plan_layer_suggestions(
    tree: model.SceneTree,
    scope: set | None = None,
    keep: set | None = None,
) -> list[LayerOp]:
    keep = keep or set()
    ops: list[LayerOp] = []
    for n in tree.walk():
        if getattr(n, "layer", None):
            continue
        if scope is not None and n.guid not in scope:
            continue
        if n.name in keep:
            continue
        suggested = None
        for anc in n.ancestors():
            if getattr(anc, "layer", None):
                suggested = anc.layer
                break
        if suggested:
            ops.append(LayerOp(node=n, layer=suggested))
    return ops
