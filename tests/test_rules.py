"""Tests for the declarative rule engine (sceneorg.rules)."""

from conftest import node

from sceneorg.core import model
from sceneorg.naming.casing import Casing
from sceneorg.naming.convention import NamingConvention
from sceneorg.structure.rules import (
    Match,
    RuleContext,
    compile_rules,
)
from sceneorg.structure.standard import GroupRule, StructureStandard


def make_ctx(tree, rules=None, casing=Casing.PASCAL, scope=None):
    standard = StructureStandard(rules or [])
    conv = NamingConvention(style=casing, language=None, number_pad=2)
    return RuleContext(tree=tree, convention=conv, standard=standard, scope=scope)


def guids(tree):
    for i, n in enumerate(tree.walk()):
        n.guid = i
    return tree


# -- compile_rules ------------------------------------------------------------

def test_compile_unknown_type_is_warning_not_crash():
    rs = compile_rules([{"type": "hologram", "x": 1}])
    assert rs.rules == []
    assert len(rs.warnings) == 1
    assert "hologram" in rs.warnings[0]


def test_compile_invalid_rule_is_warning():
    rs = compile_rules([{"type": "prefix"}])  # missing required "prefix"
    assert rs.rules == []
    assert len(rs.warnings) == 1


def test_compile_assigns_ids():
    rs = compile_rules([{"type": "prefix", "prefix": "X_"}])
    assert rs.rules[0].id == "prefix_1"


def test_rules_roundtrip_to_list():
    raw = [
        {"type": "prefix", "prefix": "LGT_", "match": {"categories": ["light"]}},
        {"type": "renumber", "pad": 3, "match": {"categories": ["mesh"]}},
        {"type": "layer", "layer": "Proxies", "match": {"types": ["Instance"]}},
        {"type": "condition", "when": {"duplicates_gt": 2},
         "then": {"suffix_scheme": "alpha"}},
    ]
    rs = compile_rules(raw)
    again = compile_rules(rs.to_list())
    assert not again.warnings
    assert [r.type for r in again.rules] == ["prefix", "renumber", "layer", "condition"]


# -- PrefixRule ---------------------------------------------------------------

def test_prefix_rule_idempotent():
    tree = guids(model.SceneTree(roots=[
        node("Key", model.CAT_LIGHT),
        node("LGT_Fill", model.CAT_LIGHT),
        node("Chair", model.CAT_MESH),
    ]))
    rs = compile_rules([{"type": "prefix", "prefix": "LGT_",
                         "match": {"categories": ["light"]}}])
    bundle = rs.plan_all(make_ctx(tree))
    assert [(o.old_name, o.new_name) for o in bundle.renames] == [("Key", "LGT_Key")]


def test_prefix_rule_contextual_under_group():
    studio = node("Studio", model.CAT_NULL, children=[
        node("Key", model.CAT_LIGHT),
    ])
    tree = guids(model.SceneTree(roots=[
        studio,
        node("Sun", model.CAT_LIGHT),   # loose light -> no prefix
    ]))
    rules = [GroupRule("Studio", priority=10)]
    rs = compile_rules([{"type": "prefix", "prefix": "LGT_",
                         "match": {"categories": ["light"],
                                   "under_group": "Studio"}}])
    bundle = rs.plan_all(make_ctx(tree, rules=rules))
    assert [(o.old_name, o.new_name) for o in bundle.renames] == [("Key", "LGT_Key")]


# -- RenumberRule -------------------------------------------------------------

def test_renumber_closes_gaps():
    parent = node("Chairs", model.CAT_NULL, children=[
        node("Chair_1", model.CAT_MESH),
        node("Chair_2", model.CAT_MESH),
        node("Chair_3", model.CAT_MESH),
        node("Chair_6", model.CAT_MESH),
        node("Chair_7", model.CAT_MESH),
        node("Chair_9", model.CAT_MESH),
    ])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "renumber", "pad": 2,
                         "match": {"categories": ["mesh"]}}])
    bundle = rs.plan_all(make_ctx(tree, casing=Casing.LOWER_SNAKE))
    news = {o.old_name: o.new_name for o in bundle.renames}
    # 1,2,3 keep their slot but gain padding; 6,7,9 -> 04,05,06
    assert news == {
        "Chair_1": "Chair_01", "Chair_2": "Chair_02", "Chair_3": "Chair_03",
        "Chair_6": "Chair_04", "Chair_7": "Chair_05", "Chair_9": "Chair_06",
    }


def test_renumber_is_idempotent():
    parent = node("Chairs", model.CAT_NULL, children=[
        node("Chair_01", model.CAT_MESH),
        node("Chair_02", model.CAT_MESH),
    ])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "renumber", "pad": 2,
                         "match": {"categories": ["mesh"]}}])
    bundle = rs.plan_all(make_ctx(tree, casing=Casing.LOWER_SNAKE))
    assert bundle.renames == []


def test_renumber_ignores_unnumbered_and_respects_series_base():
    parent = node("Stuff", model.CAT_NULL, children=[
        node("Chair", model.CAT_MESH),        # unnumbered -> untouched
        node("Table_2", model.CAT_MESH),      # own series
        node("Table_5", model.CAT_MESH),
    ])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "renumber", "pad": 2,
                         "match": {"categories": ["mesh"]}}])
    bundle = rs.plan_all(make_ctx(tree, casing=Casing.LOWER_SNAKE))
    news = {o.old_name: o.new_name for o in bundle.renames}
    assert news == {"Table_2": "Table_01", "Table_5": "Table_02"}


def test_renumber_per_parent_series_are_independent():
    room_a = node("RoomA", model.CAT_NULL, children=[
        node("Lamp_3", model.CAT_MESH), node("Lamp_8", model.CAT_MESH)])
    room_b = node("RoomB", model.CAT_NULL, children=[
        node("Lamp_5", model.CAT_MESH)])
    tree = guids(model.SceneTree(roots=[room_a, room_b]))
    rs = compile_rules([{"type": "renumber", "pad": 2,
                         "match": {"categories": ["mesh"]}}])
    bundle = rs.plan_all(make_ctx(tree, casing=Casing.LOWER_SNAKE))
    news = {o.old_name: o.new_name for o in bundle.renames}
    assert news == {"Lamp_3": "Lamp_01", "Lamp_8": "Lamp_02", "Lamp_5": "Lamp_01"}


def test_renumber_skips_names_taken_by_unmatched_siblings():
    parent = node("Stuff", model.CAT_NULL, children=[
        node("Chair_01", model.CAT_NULL),     # null, NOT matched by the rule
        node("Chair_5", model.CAT_MESH),      # would become Chair_01 -> taken
    ])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "renumber", "pad": 2,
                         "match": {"categories": ["mesh"]}}])
    bundle = rs.plan_all(make_ctx(tree, casing=Casing.LOWER_SNAKE))
    assert bundle.renames == []
    assert any("taken" in w for w in bundle.warnings)


# -- ConditionRule ------------------------------------------------------------

def test_condition_duplicates_alpha_suffix():
    parent = node("Stuff", model.CAT_NULL, children=[
        node("Cube", model.CAT_MESH), node("Cube", model.CAT_MESH),
        node("Cube", model.CAT_MESH), node("Cube", model.CAT_MESH),
        node("Sphere", model.CAT_MESH),
    ])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "condition",
                         "when": {"duplicates_gt": 3},
                         "then": {"suffix_scheme": "alpha"}}])
    bundle = rs.plan_all(make_ctx(tree, casing=Casing.LOWER_SNAKE))
    assert [o.new_name for o in bundle.renames] == [
        "Cube_A", "Cube_B", "Cube_C", "Cube_D"]


def test_condition_below_threshold_does_nothing():
    parent = node("Stuff", model.CAT_NULL, children=[
        node("Cube", model.CAT_MESH), node("Cube", model.CAT_MESH)])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "condition",
                         "when": {"duplicates_gt": 3},
                         "then": {"suffix_scheme": "alpha"}}])
    assert rs.plan_all(make_ctx(tree)).renames == []


def test_condition_assign_layer():
    tree = guids(model.SceneTree(roots=[
        node("Proxy_A", model.CAT_OTHER, type_name="Instance")]))
    rs = compile_rules([{"type": "condition",
                         "when": {"match": {"types": ["Instance"]}},
                         "then": {"assign_layer": "Proxies"}}])
    bundle = rs.plan_all(make_ctx(tree))
    assert [(o.name, o.layer) for o in bundle.layers] == [("Proxy_A", "Proxies")]


# -- LayerRule + RuleSet mechanics ---------------------------------------------

def test_layer_rule_basic():
    tree = guids(model.SceneTree(roots=[
        node("Key", model.CAT_LIGHT), node("Chair", model.CAT_MESH)]))
    rs = compile_rules([{"type": "layer", "layer": "Lights",
                         "match": {"categories": ["light"]}}])
    bundle = rs.plan_all(make_ctx(tree))
    assert [(o.name, o.layer) for o in bundle.layers] == [("Key", "Lights")]


def test_first_claim_wins_by_priority():
    tree = guids(model.SceneTree(roots=[node("Key", model.CAT_LIGHT)]))
    rs = compile_rules([
        {"id": "low", "type": "prefix", "prefix": "B_", "priority": 1,
         "match": {"categories": ["light"]}},
        {"id": "high", "type": "prefix", "prefix": "A_", "priority": 10,
         "match": {"categories": ["light"]}},
    ])
    bundle = rs.plan_all(make_ctx(tree))
    assert [o.new_name for o in bundle.renames] == ["A_Key"]
    assert bundle.applied_rules == ["high"]


def test_disabled_rule_is_skipped():
    tree = guids(model.SceneTree(roots=[node("Key", model.CAT_LIGHT)]))
    rs = compile_rules([{"type": "prefix", "prefix": "LGT_", "enabled": False,
                         "match": {"categories": ["light"]}}])
    assert rs.plan_all(make_ctx(tree)).renames == []


def test_scope_limits_rules():
    tree = guids(model.SceneTree(roots=[
        node("Key", model.CAT_LIGHT), node("Fill", model.CAT_LIGHT)]))
    key_guid = next(n.guid for n in tree.walk() if n.name == "Key")
    rs = compile_rules([{"type": "prefix", "prefix": "LGT_",
                         "match": {"categories": ["light"]}}])
    bundle = rs.plan_all(make_ctx(tree, scope={key_guid}))
    assert [o.old_name for o in bundle.renames] == ["Key"]


def test_match_name_regex_and_keywords():
    tree = guids(model.SceneTree(roots=[
        node("Stuhl Alt", model.CAT_MESH),      # German 'chair' -> keyword match
        node("Random", model.CAT_MESH),
    ]))
    m = Match(keywords={"chair"})
    ctx = make_ctx(tree)
    names = [n.name for n in tree.walk() if m.matches(n, ctx)]
    assert names == ["Stuhl Alt"]
    m2 = Match(name_regex=r"^Rand")
    names2 = [n.name for n in tree.walk() if m2.matches(n, ctx)]
    assert names2 == ["Random"]
