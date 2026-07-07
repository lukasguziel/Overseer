"""Aenderungs-Operationen als reine Datenobjekte + Planer (kein c4d).

Der Adapter fuehrt diese Operationen spaeter mit Undo im Dokument aus.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from . import model
from .convention import NamingConvention
from .structure import StructureStandard


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


# Standard-Layer-Schema: die Typ-Achse ("was ist es") gehoert in Layer, NICHT
# in die Null-Hierarchie (die die Raum-Achse traegt). So laesst sich alles eines
# Typs togglen/rendern, ohne die raeumliche Struktur flachzumachen.
# (Kategorie ODER type_name) -> Layer-Name.
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
    """Layer-Name fuer ein Objekt nach Schema (oder None = kein Layer)."""
    scheme = scheme or DEFAULT_LAYER_SCHEME
    by_type = scheme.get("types", {})
    if node.type_name in by_type:
        return by_type[node.type_name]
    return scheme.get("categories", {}).get(node.category)


def is_safe_to_reparent(node: model.SceneNode) -> bool:
    """Nur verschieben, wenn das Objekt rein organisatorisch geparentet ist.

    Kinder von Generatoren/Deformern/Meshes (Cloner, Boole, Sweep, ...) duerfen
    NICHT verschoben werden -> das aenderte das Render-Ergebnis. Heuristik:
    sicher ist nur, wessen Elternteil die Wurzel oder eine Null ist.
    """
    return node.parent is None or node.parent.category == model.CAT_NULL


def plan_renames(
    tree: model.SceneTree,
    convention: NamingConvention,
    scope: set | None = None,
    prefixes: dict | None = None,
) -> list[RenameOp]:
    """Umbenennungen fuer nicht-konforme Objekte, kollisionssicher pro Elternteil.

    scope     nur diese guids umbenennen (None = alle)
    prefixes  {kategorie: praefix} z.B. {'light': 'LGT_'} (idempotent)
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
                used.add(c.name)  # nicht umbenannte Geschwister-Namen reservieren

        for c in renaming:
            prefix = prefixes.get(c.category, "")
            raw = c.name
            if prefix and raw.startswith(prefix):
                raw = raw[len(prefix):]  # bestehendes Praefix vor Normalisierung abziehen
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
    """Umgruppierungen fuer falsch platzierte Objekte (mit Safety-Filter).

    tidy=True (Default, sicher): sammelt NUR wirklich lose Objekte ein -- solche,
    die in KEINER erkannten Gruppe stecken. Objekte, die bereits in einem
    (auch verschachtelten) Gruppen-Container liegen, werden nie herausgerissen.
    So bleibt eine durchdachte Raum-Hierarchie erhalten, statt flachgeklopft zu
    werden.

    tidy=False: aggressives Verhalten -- verschiebt auch Objekte aus einer
    'falschen' Gruppe an die Wurzel-Zielgruppe (kann Struktur zerlegen).
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
            # steckt schon in einer erkannten Gruppe -> in Ruhe lassen
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
    """Layer-Zuweisungen nach Schema (Typ-Achse), ohne die Hierarchie zu aendern."""
    ops: list[LayerOp] = []
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        layer = layer_for(n, scheme)
        if layer:
            ops.append(LayerOp(guid=n.guid, name=n.name, layer=layer))
    return ops
