from sceneorg.structure.graph import graph_from_groups


def test_graph_has_group_and_source_nodes():
    groups = [
        {"name": "Cameras", "categories": ["camera"], "keywords": [], "aliases": ["cams"], "priority": 100},
        {"name": "Furniture", "categories": [], "keywords": ["chair", "table"], "aliases": ["moebel"], "priority": 40},
    ]
    g = graph_from_groups(groups)
    types = [n["type"] for n in g["nodes"]]
    assert types.count("group") == 2
    assert "category" in types      # Cameras -> category node
    assert "keyword" in types       # Furniture -> Keyword-Node
    # every edge connects a source to a group node
    group_ids = {n["id"] for n in g["nodes"] if n["type"] == "group"}
    assert all(e["target"] in group_ids for e in g["edges"])


def test_group_node_carries_aliases_and_priority():
    g = graph_from_groups([{"name": "Lights", "categories": ["light"],
                            "aliases": ["licht", "lichter"], "priority": 100}])
    gn = next(n for n in g["nodes"] if n["type"] == "group")
    assert gn["data"]["name"] == "Lights"
    assert "licht" in gn["data"]["aliases"]
    assert gn["data"]["priority"] == 100


def test_empty_groups_give_empty_graph():
    g = graph_from_groups([])
    assert g == {"nodes": [], "edges": []}
