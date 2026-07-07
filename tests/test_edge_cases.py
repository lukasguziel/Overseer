"""Targeted tests for previously uncovered branches (coverage gaps)."""

import pytest
from conftest import node

from sceneorg import model, ops
from sceneorg.analyzer import SceneAnalyzer
from sceneorg.convention import NamingConvention
from sceneorg.detect import detect_style
from sceneorg.naming import Casing, detect_casing
from sceneorg.structure import StructureStandard
from sceneorg.translate import translate_preserving

# -- model: aggregates, traversal, lookup ----------------------------------

def _geo_tree():
    child = model.SceneNode(name="Leaf", category=model.CAT_MESH, guid=2,
                            point_count=4, poly_count=2)
    root = model.SceneNode(name="Group", category=model.CAT_NULL, guid=1,
                           point_count=1, poly_count=1)
    root.add_child(child)
    return model.SceneTree(roots=[root]), root, child


def test_subtree_aggregates_include_children():
    _, root, child = _geo_tree()
    assert root.subtree_polys == 3
    assert root.subtree_points == 5
    assert child.subtree_polys == 2


def test_descendants_excludes_self():
    _, root, child = _geo_tree()
    assert list(root.descendants()) == [child]
    assert list(child.descendants()) == []


def test_tree_find_hit_and_miss():
    tree, _, child = _geo_tree()
    assert tree.find(2) is child
    assert tree.find(999) is None


# -- analyzer: polygon stats / largest assets ------------------------------

def test_analyzer_counts_polygons(std):
    tree, _, _ = _geo_tree()
    report = SceneAnalyzer(std).analyze(tree, file_name="geo.c4d")
    assert report.total_polys == 3
    assert report.polys_by_category.get(model.CAT_MESH) == 2
    assert report.polys_by_group  # top group "Group" carries the polys
    assert report.largest and report.largest[0]["name"] in ("Leaf", "Group")


# -- naming/detect: mixed & empty names ------------------------------------

def test_detect_casing_mixed_and_empty():
    assert detect_casing("MyChair_big") is Casing.MIXED
    assert detect_casing("") is Casing.EMPTY


def test_detect_style_skips_mixed_and_empty():
    style, conf, raw = detect_style(["MyChair_big", "", "Chair", "Table"])
    assert style is Casing.PASCAL
    assert "mixed" not in raw and "empty" not in raw  # skipped entirely


# -- convention: word passthrough for Pascal/camel styles ------------------

def test_pascal_normalize_keeps_word_casing_via_fallback():
    conv = NamingConvention(style=Casing.PASCAL, language=None, number_pad=2)
    assert conv.normalize("kitchen chair 3") == "KitchenChair03"


# -- ops: layer scheme by type, scope filters, unnormalizable names --------

def test_layer_for_matches_type_before_category():
    inst = node("Tree Proxy", model.CAT_MESH, type_name="Instance")
    assert ops.layer_for(inst) == "Proxies"


def test_plan_layers_respects_scope():
    light_a = node("Key", model.CAT_LIGHT, guid=1)
    light_b = node("Fill", model.CAT_LIGHT, guid=2)
    tree = model.SceneTree(roots=[light_a, light_b])
    planned = ops.plan_layers(tree, scope={2})
    assert [o.guid for o in planned] == [2]


def test_plan_reparents_respects_scope(std, sample_tree):
    all_ops = ops.plan_reparents(sample_tree, std, safe_only=False, tidy=False)
    assert all_ops  # sample tree contains misplaced objects
    scoped = ops.plan_reparents(sample_tree, std, scope=set(),
                                safe_only=False, tidy=False)
    assert scoped == []


def test_plan_renames_skips_prefix_only_name():
    conv = NamingConvention(style=Casing.UPPER_SNAKE, language=None, number_pad=2)
    bare = node("L_", model.CAT_LIGHT, guid=1)  # strips to empty base
    tree = model.SceneTree(roots=[bare])
    planned = ops.plan_renames(tree, conv, prefixes={model.CAT_LIGHT: "L_"})
    assert planned == []


# -- structure: empty scene, canonical group of None -----------------------

def test_compliance_is_full_on_empty_scene(std):
    report = std.evaluate(model.SceneTree(roots=[]))
    assert report.compliance == 1.0


def test_canonical_group_none_passthrough():
    assert StructureStandard([]).canonical_group(None) is None


# -- translate: casing transfer branches -----------------------------------

def test_translate_preserves_lower_and_capitalized_case():
    assert translate_preserving("stuhl")[0] == "chair"
    assert translate_preserving("Stuhl")[0] == "Chair"
    assert translate_preserving("STUHL")[0] == "CHAIR"


def test_translate_mixed_case_falls_back_to_plain_translation():
    assert translate_preserving("StUhl")[0] == "chair"


def test_non_producible_style_is_rejected():
    with pytest.raises(ValueError):
        NamingConvention(style=Casing.CAPITALIZED, language=None, number_pad=2)
