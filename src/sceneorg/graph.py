"""Generate the node-editor layout from group rules (pure, no c4d).

The Rules tab (RuleGraph.jsx) renders ONLY from a stored `graph`
(nodes/edges). Presets/the skill however only provide `groups` -> this
function builds the matching layout so a loaded preset shows up in the
editor immediately.
"""

from __future__ import annotations


def graph_from_structure(structure: list[dict]) -> dict:
    """Builds {nodes, edges} from a NESTED structure tree (config schema 2).

    Child groups connect to their parent group via a group->group edge; the
    editor reads that edge back as the `parent` relation. Depth shifts the
    x position so nesting is visible at a glance.
    """
    nodes: list[dict] = []
    edges: list[dict] = []
    nid = [1]
    row = [0]

    def new_id(t: str) -> str:
        i = "%s_%d" % (t, nid[0])
        nid[0] += 1
        return i

    def emit(group: dict, depth: int, parent_gid: str | None) -> None:
        y = row[0] * 190
        gid = new_id("group")
        nodes.append({
            "id": gid, "type": "group",
            "position": {"x": 520 + depth * 260, "y": y},
            "data": {
                "name": group.get("name", "Group"),
                "aliases": ", ".join(group.get("aliases", [])),
                "priority": group.get("priority", 50),
            },
        })
        if parent_gid:
            edges.append({"id": "e_%s_%s" % (gid, parent_gid),
                          "source": gid, "target": parent_gid,
                          "animated": False})
        for cat in group.get("categories", []):
            cid = new_id("category")
            nodes.append({"id": cid, "type": "category",
                          "position": {"x": 60, "y": y},
                          "data": {"category": cat}})
            edges.append({"id": "e_%s_%s" % (cid, gid),
                          "source": cid, "target": gid, "animated": True})
            y += 70
        if group.get("keywords"):
            kid = new_id("keyword")
            nodes.append({"id": kid, "type": "keyword",
                          "position": {"x": 270, "y": row[0] * 190},
                          "data": {"keywords": ", ".join(group["keywords"])}})
            edges.append({"id": "e_%s_%s" % (kid, gid),
                          "source": kid, "target": gid, "animated": True})
        row[0] += 1
        for child in group.get("children", []) or []:
            emit(child, depth + 1, gid)

    for g in structure or []:
        emit(g, 0, None)
    return {"nodes": nodes, "edges": edges}


def graph_from_groups(groups: list[dict]) -> dict:
    """Builds {nodes, edges} for React Flow from a list of groups.

    One group node per group (right); one category node per category and one
    keyword node per keyword set (left), connected via edges. IDs follow the
    `<type>_<n>` scheme the editor expects when re-counting.
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
