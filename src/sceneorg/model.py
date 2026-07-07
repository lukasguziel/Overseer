"""Reines Datenmodell der Szenen-Hierarchie (kein c4d)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

# Kategorien (bewusst als Strings, damit JSON-freundlich)
CAT_LIGHT = "light"
CAT_CAMERA = "camera"
CAT_NULL = "null"
CAT_MESH = "mesh"
CAT_SPLINE = "spline"
CAT_OTHER = "other"

ALL_CATEGORIES = (CAT_LIGHT, CAT_CAMERA, CAT_NULL, CAT_MESH, CAT_SPLINE, CAT_OTHER)


@dataclass
class SceneNode:
    """Ein Objekt der Szene, entkoppelt vom c4d.BaseObject.

    `guid` ist ein stabiler Index, ueber den der Adapter das echte
    c4d-Objekt zuordnet, um Aenderungen zurueckzuschreiben.
    """

    name: str
    type_name: str = "Null"
    category: str = CAT_OTHER
    guid: int = -1
    depth: int = 0
    point_count: int = 0   # eigene + Cache-Punkte dieses Objekts
    poly_count: int = 0    # eigene + Cache-Polygone dieses Objekts
    parent: SceneNode | None = field(default=None, repr=False)
    children: list[SceneNode] = field(default_factory=list, repr=False)

    # -- Aggregate --------------------------------------------------------
    @property
    def subtree_polys(self) -> int:
        """Polygone dieses Knotens inklusive aller Kind-Objekte (Szenengraph)."""
        return self.poly_count + sum(c.subtree_polys for c in self.children)

    @property
    def subtree_points(self) -> int:
        return self.point_count + sum(c.subtree_points for c in self.children)

    # -- Aufbau -----------------------------------------------------------
    def add_child(self, child: SceneNode) -> SceneNode:
        child.parent = self
        child.depth = self.depth + 1
        self.children.append(child)
        return child

    # -- Traversierung ----------------------------------------------------
    def walk(self) -> Iterator[SceneNode]:
        """Praeorder ueber diesen Knoten und alle Nachfahren."""
        yield self
        for c in self.children:
            yield from c.walk()

    def descendants(self) -> Iterator[SceneNode]:
        for c in self.children:
            yield from c.walk()

    def ancestors(self) -> Iterator[SceneNode]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def top_group(self) -> SceneNode:
        """Oberster Vorfahre (Top-Level-Knoten) dieses Knotens."""
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    @property
    def path(self) -> str:
        parts = [self.name]
        for anc in self.ancestors():
            parts.append(anc.name)
        return "/" + "/".join(reversed(parts))

    @property
    def child_count(self) -> int:
        return len(self.children)


@dataclass
class SceneTree:
    """Wrapper um die Wurzel-Knoten (ein Dokument hat mehrere Top-Level-Objekte)."""

    roots: list[SceneNode] = field(default_factory=list)

    def walk(self) -> Iterator[SceneNode]:
        for r in self.roots:
            yield from r.walk()

    def all_nodes(self) -> list[SceneNode]:
        return list(self.walk())

    def by_category(self, category: str) -> list[SceneNode]:
        return [n for n in self.walk() if n.category == category]

    def find(self, guid: int) -> SceneNode | None:
        for n in self.walk():
            if n.guid == guid:
                return n
        return None
