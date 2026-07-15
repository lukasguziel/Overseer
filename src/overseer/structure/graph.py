from __future__ import annotations

_ROW_PITCH = 190
_CATEGORY_PITCH = 70


def graph_from_structure(structure: list[dict]) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    nid = [1]
    top = [0]

    def new_id(t: str) -> str:
        i = "%s_%d" % (t, nid[0])
        nid[0] += 1
        return i

    def emit(group: dict, depth: int, parent_gid: str | None) -> None:
        y = top[0]
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

        cat_y = y
        for cat in group.get("categories", []):
            cid = new_id("category")
            nodes.append({"id": cid, "type": "category",
                          "position": {"x": 60, "y": cat_y},
                          "data": {"category": cat}})
            edges.append({"id": "e_%s_%s" % (cid, gid),
                          "source": cid, "target": gid, "animated": True})
            cat_y += _CATEGORY_PITCH

        if group.get("keywords"):
            kid = new_id("keyword")
            nodes.append({"id": kid, "type": "keyword",
                          "position": {"x": 270, "y": y},
                          "data": {"keywords": ", ".join(group["keywords"])}})
            edges.append({"id": "e_%s_%s" % (kid, gid),
                          "source": kid, "target": gid, "animated": True})

        top[0] = max(y + _ROW_PITCH, cat_y)
        for child in group.get("children", []) or []:
            emit(child, depth + 1, gid)

    for g in structure or []:
        emit(g, 0, None)

    return {"nodes": nodes, "edges": edges}


def graph_from_groups(groups: list[dict]) -> dict:
    return graph_from_structure(groups)
