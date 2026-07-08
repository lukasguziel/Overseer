from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..naming.convention import NamingConvention
from ..structure.standard import StructureStandard
from . import model


@dataclass
class RenameOp:
    guid: int
    old_name: str
    new_name: str


@dataclass
class ReparentOp:
    guid: int
    name: str
    from_group: str
    to_group: str


@dataclass
class LayerOp:
    guid: int
    name: str
    layer: str


DEFAULT_LAYER_SCHEME = {
    "categories": {
        model.CAT_LIGHT: "Lights",
        model.CAT_CAMERA: "Cameras",
    },
    "types": {
        "Instance": "Proxies",
    },
}


def layer_for(node: model.SceneNode, scheme: dict | None = None) -> str | None:
    scheme = scheme or DEFAULT_LAYER_SCHEME
    by_type = scheme.get("types", {})
    if node.type_name in by_type:
        return by_type[node.type_name]
    return scheme.get("categories", {}).get(node.category)


def is_safe_to_reparent(node: model.SceneNode) -> bool:
    return node.parent is None or node.parent.category == model.CAT_NULL


def plan_renames(
    tree: model.SceneTree,
    convention: NamingConvention,
    scope: set | None = None,
    prefixes: dict | None = None,
) -> list[RenameOp]:
    prefixes = prefixes or {}
    buckets: dict = defaultdict(list)
    for n in tree.walk():
        key = id(n.parent) if n.parent is not None else None
        buckets[key].append(n)

    ops: list[RenameOp] = []
    for children in buckets.values():
        used: set = set()
        renaming = []
        for c in children:
            if scope is None or c.guid in scope:
                renaming.append(c)
            else:
                used.add(c.name)

        for c in renaming:
            prefix = prefixes.get(c.category, "")
            raw = c.name
            if prefix and raw.startswith(prefix):
                raw = raw[len(prefix):]
            base = convention.normalize(raw)
            if not base:
                used.add(c.name)
                continue
            if prefix:
                base = prefix + base

            final = base
            i = 1
            while final in used:
                final = convention.disambiguate(base, i)
                i += 1
            used.add(final)
            if final != c.name:
                ops.append(RenameOp(guid=c.guid, old_name=c.name, new_name=final))
    return ops


def plan_reparents(
    tree: model.SceneTree,
    standard: StructureStandard,
    scope: set | None = None,
    safe_only: bool = True,
    tidy: bool = True,
) -> list[ReparentOp]:
    report = standard.evaluate(tree)
    node_by_guid = {n.guid: n for n in tree.walk()}

    ops: list[ReparentOp] = []
    for f in report.misplaced:
        if scope is not None and f.guid not in scope:
            continue
        node = node_by_guid.get(f.guid)
        if safe_only and node is not None and not is_safe_to_reparent(node):
            continue
        if tidy and node is not None and standard.enclosing_group(node) is not None:
            continue
        ops.append(ReparentOp(
            guid=f.guid,
            name=f.name,
            from_group=f.current_group or "(root)",
            to_group=f.expected_group,
        ))
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
        if layer:
            ops.append(LayerOp(guid=n.guid, name=n.name, layer=layer))
    return ops
