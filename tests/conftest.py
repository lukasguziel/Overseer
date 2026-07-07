"""Shared test helpers: building SceneTrees without c4d."""

import pytest

from sceneorg import model
from sceneorg.structure import GroupRule, StructureStandard


def node(name, category=model.CAT_OTHER, type_name=None, guid=-1, children=None):
    n = model.SceneNode(
        name=name,
        type_name=type_name or category.capitalize(),
        category=category,
        guid=guid,
    )
    for c in (children or []):
        n.add_child(c)
    return n


def archviz_standard():
    """Explicit rule set for the tests (no longer part of the product default)."""
    return StructureStandard([
        GroupRule("Cameras", match_categories={model.CAT_CAMERA},
                  aliases={"kameras"}, priority=100),
        GroupRule("Lights", match_categories={model.CAT_LIGHT},
                  aliases={"lichter", "beleuchtung"}, priority=100),
        GroupRule("Furniture", match_keywords={
            "furniture", "chair", "table", "sofa", "couch", "bed", "cabinet",
            "shelf", "lamp", "curtain", "mirror", "carpet", "pillow", "desk",
        }, aliases={"moebel"}, priority=50),
        GroupRule("Exterior", match_keywords={
            "exterior", "facade", "roof", "garden", "yard", "tree", "plant",
            "building", "fence", "terrain", "street",
        }, aliases={"aussen"}, priority=40),
        GroupRule("Interior", match_keywords={
            "interior", "wall", "floor", "ceiling", "window", "door", "stairs",
            "column", "room", "kitchen", "bathroom",
        }, aliases={"innen"}, priority=30),
    ])


@pytest.fixture
def std():
    return archviz_standard()


@pytest.fixture
def sample_tree():
    """Deliberately mixed scene: partly grouped correctly, partly chaos."""
    g = [0]

    def nid(name, cat, kids=None):
        n = node(name, cat, guid=g[0], children=kids)
        g[0] += 1
        return n

    lights = nid("Lights", model.CAT_NULL, [
        nid("LIGHT_KEY", model.CAT_LIGHT),
        nid("light_fill", model.CAT_LIGHT),
    ])
    furniture = nid("Furniture", model.CAT_NULL, [
        nid("Stuhl_01", model.CAT_MESH),
        nid("Table", model.CAT_MESH),
    ])
    loose_cam = nid("KAMERA MAIN", model.CAT_CAMERA)
    exterior = nid("Exterior", model.CAT_NULL, [
        nid("Sofa", model.CAT_MESH),
        nid("Baum_02", model.CAT_MESH),
    ])
    tree = model.SceneTree(roots=[lights, furniture, loose_cam, exterior])
    return tree
