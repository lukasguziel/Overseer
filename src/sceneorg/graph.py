"""Node-Editor-Layout aus Gruppen-Regeln erzeugen (rein, kein c4d).

Der Rules-Tab (RuleGraph.jsx) rendert NUR aus einem gespeicherten `graph`
(nodes/edges). Presets/der Skill liefern aber nur `groups` -> diese Funktion
baut das passende Layout, damit ein geladenes Preset sofort im Editor erscheint.
"""

from __future__ import annotations


def graph_from_groups(groups: list[dict]) -> dict:
    """Baut {nodes, edges} fuer React Flow aus einer Gruppen-Liste.

    Pro Gruppe ein Group-Node (rechts); je Kategorie ein Category-Node und je
    Keyword-Menge ein Keyword-Node (links), per Edge verbunden. IDs im Schema
    `<typ>_<n>`, das der Editor beim Nachzaehlen erwartet.
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    nid = [1]

    def new_id(t: str) -> str:
        i = "%s_%d" % (t, nid[0])
        nid[0] += 1
        return i

    for gi, g in enumerate(groups):
        y = gi * 190
        gid = new_id("group")
        nodes.append({
            "id": gid, "type": "group", "position": {"x": 520, "y": y},
            "data": {
                "name": g.get("name", "Group"),
                "aliases": ", ".join(g.get("aliases", [])),
                "priority": g.get("priority", 50),
            },
        })
        for cat in g.get("categories", []):
            cid = new_id("category")
            nodes.append({"id": cid, "type": "category",
                          "position": {"x": 60, "y": y},
                          "data": {"category": cat}})
            edges.append({"id": "e_%s_%s" % (cid, gid),
                          "source": cid, "target": gid, "animated": True})
            y += 70
        if g.get("keywords"):
            kid = new_id("keyword")
            nodes.append({"id": kid, "type": "keyword",
                          "position": {"x": 270, "y": gi * 190},
                          "data": {"keywords": ", ".join(g["keywords"])}})
            edges.append({"id": "e_%s_%s" % (kid, gid),
                          "source": kid, "target": gid, "animated": True})
    return {"nodes": nodes, "edges": edges}
