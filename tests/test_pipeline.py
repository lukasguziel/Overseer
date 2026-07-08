"""Combined one-click planning (sceneorg.pipeline)."""

from conftest import node

from sceneorg.config import load_config
from sceneorg.core import model
from sceneorg.core.pipeline import filter_accepted, plan_combined


def build_tree():
    tree = model.SceneTree(roots=[
        node("key light", model.CAT_LIGHT),        # loose -> Lights + rename
        node("Lights", model.CAT_NULL, children=[
            node("Fill", model.CAT_LIGHT),
        ]),
    ])
    for i, n in enumerate(tree.walk()):
        n.guid = i
    return tree


CFG = {
    "schema": 2,
    "casing": "PascalCase",
    "language": "en",
    "structure": [{"name": "Lights", "categories": ["light"], "priority": 100}],
    "rules": [
        {"id": "lgt", "type": "prefix", "prefix": "LGT_",
         "match": {"categories": ["light"]}, "priority": 10},
    ],
}


def test_plan_combined_merges_rules_and_naming():
    # setup
    cfg = load_config(CFG)

    # do it
    plan = plan_combined(build_tree(), cfg)

    # postcondition
    renames = {r.old_name: r.new_name for r in plan.renames}
    assert renames["key light"] == "LGT_key light"  # rule claims first: prefix, not convention
    assert renames["Fill"] == "LGT_Fill"
    assert "lgt" in plan.applied_rules
    assert [r.to_group for r in plan.reparents] == ["Lights"]  # loose light routed into Lights
    assert {(o.name, o.layer) for o in plan.layers} == {
        ("key light", "Lights"), ("Fill", "Lights")}  # default layer scheme fires too


def test_plan_combined_naming_fills_unclaimed():
    # setup
    cfg = load_config({"schema": 2, "casing": "PascalCase", "language": "en",
                       "structure": CFG["structure"]})

    # do it
    plan = plan_combined(build_tree(), cfg)

    # postcondition
    renames = {r.old_name: r.new_name for r in plan.renames}
    assert renames["key light"] == "KeyLight"   # pure convention rename


def test_filter_accepted_sections():
    # setup
    cfg = load_config(CFG)
    plan = plan_combined(build_tree(), cfg)
    keep = plan.renames[0].guid

    # do it
    chosen = filter_accepted(plan, {"naming": [keep], "structure": []})

    # postcondition
    assert [r.guid for r in chosen.renames] == [keep]
    assert chosen.reparents == []
    assert len(chosen.layers) == len(plan.layers)   # missing key = accept all
