from conftest import node

from overseer.core import model
from overseer.naming.casing import Casing
from overseer.naming.convention import NamingConvention
from overseer.structure.rules import RuleContext, compile_rules
from overseer.structure.standard import GroupRule, StructureStandard


def make_ctx(tree, rules=None, casing=Casing.LOWER_SNAKE, pad=2):
    standard = StructureStandard(rules or [])
    conv = NamingConvention(style=casing, language=None, number_pad=pad)
    return RuleContext(tree=tree, convention=conv, standard=standard)


def guids(tree):
    for i, n in enumerate(tree.walk()):
        n.guid = i
    return tree


def test_compile_rules_warns_on_non_dict_entry():
    # do it
    rs = compile_rules(["prefix", None, 7])

    # postcondition: no AttributeError, every bad entry becomes a warning
    assert rs.rules == []
    assert len(rs.warnings) == 3


def test_compile_rules_warns_on_invalid_name_regex():
    # do it
    rs = compile_rules([{"type": "prefix", "prefix": "X_",
                         "match": {"name_regex": "[A-"}}])

    # postcondition: the broken pattern is reported instead of matching nothing
    assert rs.rules == []
    assert any("name_regex" in w for w in rs.warnings)


def test_compile_rules_warns_on_invalid_name_regex_in_condition_when():
    # do it
    rs = compile_rules([{"type": "condition",
                         "when": {"match": {"name_regex": "*bad"}},
                         "then": {"apply_prefix": "X_"}}])

    # postcondition
    assert rs.rules == []
    assert any("name_regex" in w for w in rs.warnings)


def test_renumber_reserves_root_level_sibling_names():
    # setup: flat scene -- the unmatched null already owns Chair_01
    tree = guids(model.SceneTree(roots=[
        node("Chair_01", model.CAT_NULL),
        node("Chair_5", model.CAT_MESH),
    ]))
    rs = compile_rules([{"type": "renumber", "pad": 2,
                         "match": {"categories": ["mesh"]}}])

    # do it
    bundle = rs.plan_all(make_ctx(tree))

    # postcondition
    assert bundle.renames == []
    assert any("taken" in w for w in bundle.warnings)


def test_renumber_keeps_existing_numeric_order_regardless_of_walk_order():
    # setup: document order (5 before 2) contradicts numeric order
    parent = node("Chairs", model.CAT_NULL, children=[
        node("Chair_5", model.CAT_MESH),
        node("Chair_2", model.CAT_MESH),
    ])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "renumber", "pad": 2,
                         "match": {"categories": ["mesh"]}}])

    # do it
    bundle = rs.plan_all(make_ctx(tree))

    # postcondition: numbers are not swapped
    news = {o.old_name: o.new_name for o in bundle.renames}
    assert news == {"Chair_2": "Chair_01", "Chair_5": "Chair_02"}


def test_condition_suffix_skips_names_taken_by_siblings():
    # setup: Cube_A already exists next to the duplicates
    parent = node("Stuff", model.CAT_NULL, children=[
        node("Cube", model.CAT_MESH),
        node("Cube", model.CAT_MESH),
        node("Cube_A", model.CAT_MESH),
    ])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "condition",
                         "when": {"duplicates_gt": 1,
                                  "match": {"name_regex": "^Cube$"}},
                         "then": {"suffix_scheme": "alpha"}}])

    # do it
    bundle = rs.plan_all(make_ctx(tree))

    # postcondition: the rule steps over the taken suffix instead of colliding
    assert [o.new_name for o in bundle.renames] == ["Cube_B", "Cube_C"]


def test_condition_numeric_suffix_uses_convention_pad():
    # setup
    parent = node("Stuff", model.CAT_NULL, children=[
        node("Cube", model.CAT_MESH), node("Cube", model.CAT_MESH)])
    tree = guids(model.SceneTree(roots=[parent]))
    rs = compile_rules([{"type": "condition",
                         "when": {"duplicates_gt": 1},
                         "then": {"suffix_scheme": "numeric"}}])

    # do it
    bundle = rs.plan_all(make_ctx(tree, pad=3))

    # postcondition
    assert [o.new_name for o in bundle.renames] == ["Cube_001", "Cube_002"]


def test_container_rule_disambiguates_below_the_declared_parent():
    # setup: the Props container sits one level below its declared parent Interior
    standard = StructureStandard([
        GroupRule("Interior", priority=50),
        GroupRule("Room", parent="Interior", priority=40),
        GroupRule("Props", parent="Exterior", priority=90),
        GroupRule("Props", parent="Interior", priority=30),
    ])
    props = node("Props", model.CAT_NULL)
    room = node("Room", model.CAT_NULL, children=[props])
    interior = node("Interior", model.CAT_NULL, children=[room])
    guids(model.SceneTree(roots=[interior]))

    # do it
    rule = standard.container_rule(props)

    # postcondition
    assert rule is not None
    assert rule.path == "Interior/Props"
