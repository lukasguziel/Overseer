"""Change operations as pure data objects + planners (no c4d).

The adapter later executes these operations in the document with undo support.
"""

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


# Default layer scheme: the type axis ("what is it") belongs in layers, NOT
# in the null hierarchy (which carries the spatial axis). This way everything
# of one type can be toggled/rendered without flattening the spatial structure.
# (category OR type_name) -> layer name.
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
    """Layer name for an object per scheme (or None = no layer)."""
    scheme = scheme or DEFAULT_LAYER_SCHEME
    by_type = scheme.get("types", {})
    if node.type_name in by_type:
        return by_type[node.type_name]
    return scheme.get("categories", {}).get(node.category)


def is_safe_to_reparent(node: model.SceneNode) -> bool:
    """Only move if the object is parented purely for organization.

    Children of generators/deformers/meshes (Cloner, Boole, Sweep, ...) must
    NOT be moved -> that would change the render result. Heuristic: only
    objects whose parent is the root or a null are safe.
    """
    return node.parent is None or node.parent.category == model.CAT_NULL


def plan_renames(
    tree: model.SceneTree,
    convention: NamingConvention,
    scope: set | None = None,
    prefixes: dict | None = None,
) -> list[RenameOp]:
    """Renames for non-conforming objects, collision-safe per parent.

    scope     only rename these guids (None = all)
    prefixes  {category: prefix} e.g. {'light': 'LGT_'} (idempotent)
    """
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
                used.add(c.name)  # reserve names of siblings that are not renamed

        for c in renaming:
            prefix = prefixes.get(c.category, "")
            raw = c.name
            if prefix and raw.startswith(prefix):
                raw = raw[len(prefix):]  # strip existing prefix before normalizing
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
    """Regroupings for misplaced objects (with safety filter).

    tidy=True (default, safe): collects ONLY truly loose objects -- those that
    sit in NO recognized group. Objects that already live in a (possibly
    nested) group container are never ripped out. This preserves a
    well-thought-out spatial hierarchy instead of flattening it.

    tidy=False: aggressive behavior -- also moves objects out of a 'wrong'
    group to the root-level target group (can tear apart the structure).
    """
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
            # already inside a recognized group -> leave it alone
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
    """Layer assignments per scheme (type axis) without changing the hierarchy."""
    ops: list[LayerOp] = []
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        layer = layer_for(n, scheme)
        if layer:
            ops.append(LayerOp(guid=n.guid, name=n.name, layer=layer))
    return ops
