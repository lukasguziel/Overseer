import pytest
from conftest import node

from overseer.core.naming.casing import Casing, detect_casing
from overseer.core.naming.convention import NamingConvention
from overseer.core.naming.detect import detect_style
from overseer.core.naming.translate import translate_preserving
from overseer.core.organize import ops
from overseer.core.scene import model
from overseer.core.scene.analyzer import SceneAnalyzer

# -- model: aggregates, traversal, lookup ----------------------------------

def _geo_tree():
    child = model.SceneNode(name="Leaf", category=model.CAT_MESH, guid=2,
                            point_count=4, poly_count=2)
    root = model.SceneNode(name="Group", category=model.CAT_NULL, guid=1,
                           point_count=1, poly_count=1)
    root.add_child(child)
    return model.SceneTree(roots=[root]), root, child


def test_subtree_aggregates_include_children():
    # setup
    _, root, child = _geo_tree()

    # postcondition
    assert root.subtree_polys == 3
    assert root.subtree_points == 5
    assert child.subtree_polys == 2


def test_descendants_excludes_self():
    # setup
    _, root, child = _geo_tree()

    # postcondition
    assert list(root.descendants()) == [child]
    assert list(child.descendants()) == []


def test_tree_find_hit_and_miss():
    # setup
    tree, _, child = _geo_tree()

    # postcondition
    assert tree.find(2) is child
    assert tree.find(999) is None


# -- analyzer: polygon stats / largest assets ------------------------------

def test_analyzer_counts_polygons():
    # setup
    tree, _, _ = _geo_tree()

    # do it
    report = SceneAnalyzer().analyze(tree, file_name="geo.c4d")

    # postcondition
    assert report.total_polys == 3
    assert report.polys_by_category.get(model.CAT_MESH) == 2
    assert report.polys_by_group  # top group "Group" carries the polys
    assert report.largest and report.largest[0]["name"] in ("Leaf", "Group")


def test_analyzer_scope_narrows_all_stats(sample_tree):
    # do it: scope = the "Lights" container subtree (guids 0..2 in the fixture)
    full = SceneAnalyzer().analyze(sample_tree)
    scoped = SceneAnalyzer().analyze(sample_tree, scope={0, 1, 2})

    # postcondition
    assert scoped.object_count == 3 < full.object_count
    assert scoped.categories.get("light") == 2
    assert "camera" not in scoped.categories
    assert len(scoped.nodes) == 3
    assert [t["name"] for t in scoped.top_level] == ["Lights"]  # topmost scoped node replaces tree.roots in top_level


# -- naming/detect: mixed & empty names ------------------------------------

def test_detect_casing_mixed_and_empty():
    # postcondition
    assert detect_casing("MyChair_big") is Casing.MIXED
    assert detect_casing("") is Casing.EMPTY


def test_detect_style_skips_mixed_and_empty():
    # do it
    style, conf, raw = detect_style(["MyChair_big", "", "Chair", "Table"])

    # postcondition
    assert style is Casing.PASCAL
    assert "mixed" not in raw and "empty" not in raw  # skipped entirely


# -- convention: word passthrough for Pascal/camel styles ------------------

def test_pascal_normalize_keeps_word_casing_via_fallback():
    # setup
    conv = NamingConvention(style=Casing.PASCAL, language=None, number_pad=2)

    # postcondition
    assert conv.normalize("kitchen chair 3") == "KitchenChair03"


# -- ops: layer scheme by type, scope filters, unnormalizable names --------

def test_layer_for_matches_type_before_category():
    # setup
    inst = node("Tree Proxy", model.CAT_MESH, type_name="Instance")

    # postcondition
    assert ops.layer_for(inst) == "Proxies"


def test_plan_layers_respects_scope():
    # setup
    light_a = node("Key", model.CAT_LIGHT, guid=1)
    light_b = node("Fill", model.CAT_LIGHT, guid=2)
    tree = model.SceneTree(roots=[light_a, light_b])

    # do it
    planned = ops.plan_layers(tree, scope={2})

    # postcondition
    assert [o.guid for o in planned] == [2]


def test_plan_renames_skips_unnormalizable_name():
    # setup
    conv = NamingConvention(style=Casing.UPPER_SNAKE, language=None, number_pad=2)
    bare = node("_", model.CAT_LIGHT, guid=1)  # normalizes to an empty base
    tree = model.SceneTree(roots=[bare])

    # do it
    planned = ops.plan_renames(tree, conv)

    # postcondition
    assert planned == []


# -- translate: casing transfer branches -----------------------------------

def test_translate_preserves_lower_and_capitalized_case():
    # postcondition
    assert translate_preserving("stuhl")[0] == "chair"
    assert translate_preserving("Stuhl")[0] == "Chair"
    assert translate_preserving("STUHL")[0] == "CHAIR"


def test_translate_mixed_case_falls_back_to_plain_translation():
    # postcondition
    assert translate_preserving("StUhl")[0] == "chair"


def test_non_producible_style_is_rejected():
    # postcondition
    with pytest.raises(ValueError):
        NamingConvention(style=Casing.CAPITALIZED, language=None, number_pad=2)
