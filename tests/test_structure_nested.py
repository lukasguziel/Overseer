"""Nested group structures (paths) + config v2 migration."""

from conftest import node

from sceneorg.config import load_config, migrate_config, structure_to_list
from sceneorg.core import model
from sceneorg.structure.standard import GroupRule, StructureStandard


def nested_standard():
    return StructureStandard([
        GroupRule("Room", priority=10),
        GroupRule("Furniture", match_keywords={"chair", "sofa", "table"},
                  aliases={"moebel"}, priority=50, parent="Room"),
        GroupRule("Lights", match_categories={model.CAT_LIGHT}, priority=100),
    ])


def test_group_rule_path():
    r = GroupRule("Furniture", parent="Room")
    assert r.path == "Room/Furniture"
    assert GroupRule("Lights").path == "Lights"


def test_target_group_returns_path():
    std = nested_standard()
    chair = node("Chair", model.CAT_MESH)
    assert std.target_group_for(chair) == "Room/Furniture"


def test_nested_compliance_positive():
    """Chair in Room > Furniture is compliant -- the flat model's 0.0
    false negative must not reappear."""
    std = nested_standard()
    room = node("Room", model.CAT_NULL, children=[
        node("Furniture", model.CAT_NULL, children=[
            node("Chair", model.CAT_MESH, guid=1),
        ]),
    ])
    tree = model.SceneTree(roots=[room])
    report = std.evaluate(tree)
    findings = {f.guid: f for f in report.findings}
    assert findings[1].misplaced is False
    assert findings[1].current_group == "Room/Furniture"


def test_deeper_nesting_still_complies():
    """An object below the expected group (extra custom null) still counts."""
    std = nested_standard()
    tree = model.SceneTree(roots=[
        node("Lights", model.CAT_NULL, children=[
            node("Interior", model.CAT_NULL, children=[
                node("Key", model.CAT_LIGHT, guid=1),
            ]),
        ]),
    ])
    report = std.evaluate(tree)
    assert report.findings[0].misplaced is False


def test_wrong_level_is_misplaced():
    """Furniture object directly in Room (not in Room/Furniture) is loose."""
    std = nested_standard()
    tree = model.SceneTree(roots=[
        node("Room", model.CAT_NULL, children=[
            node("Chair", model.CAT_MESH, guid=1),
        ]),
    ])
    report = std.evaluate(tree)
    f = report.findings[0]
    assert f.misplaced is True
    assert f.current_group == "Room"
    assert f.expected_group == "Room/Furniture"


def test_container_rule_disambiguates_by_parent():
    std = StructureStandard([
        GroupRule("Room", priority=10),
        GroupRule("Studio", priority=10),
        GroupRule("Lights", parent="Room", priority=50,
                  match_categories={model.CAT_LIGHT}),
        GroupRule("Lights", parent="Studio", priority=40),
    ])
    room = node("Room", model.CAT_NULL, children=[
        node("Lights", model.CAT_NULL)])
    model.SceneTree(roots=[room])
    lights_container = room.children[0]
    rule = std.container_rule(lights_container)
    assert rule is not None and rule.parent == "Room"


# -- config v2 / migration -----------------------------------------------------

V1_CONFIG = {
    "casing": "lower_snake",
    "language": "de",
    "number_pad": 3,
    "prefixes": {"light": "LGT_", "camera": "CAM_"},
    "groups": [
        {"name": "Furniture", "keywords": ["chair"], "aliases": ["Moebel"],
         "priority": 50},
    ],
    "translations": {"tuer": "door"},
    "preset": "old",
}


def test_migrate_v1_to_current():
    out = migrate_config(V1_CONFIG)
    assert out["schema"] == 3
    assert "prefixes" not in out and "groups" not in out
    prefix_rules = [r for r in out["rules"] if r["type"] == "prefix"]
    assert {r["prefix"] for r in prefix_rules} == {"LGT_", "CAM_"}
    assert out["structure"][0]["name"] == "Furniture"
    assert out["translations"] == {"tuer": "door"}   # untouched keys survive
    assert out["preset"] == "old"


def test_migrate_is_idempotent():
    once = migrate_config(V1_CONFIG)
    twice = migrate_config(once)
    assert once == twice


def test_load_config_v1_keeps_legacy_prefix_view():
    cfg = load_config(V1_CONFIG)
    assert cfg.prefixes == {"light": "LGT_", "camera": "CAM_"}
    assert cfg.convention.number_pad == 3
    assert "Furniture" in cfg.standard.group_names


def test_load_config_contextual_prefix_not_in_legacy_view():
    cfg = load_config({
        "schema": 2,
        "rules": [{"type": "prefix", "prefix": "LGT_",
                   "match": {"categories": ["light"], "under_group": "Studio"}}],
    })
    assert cfg.prefixes == {}          # contextual rules cannot be flattened
    assert len(cfg.rules.rules) == 1


def test_nested_structure_roundtrip():
    cfg = load_config({
        "schema": 2,
        "structure": [
            {"name": "Room", "children": [
                {"name": "Furniture", "keywords": ["chair"], "priority": 50},
            ]},
            {"name": "Lights", "categories": ["light"], "priority": 100},
        ],
    })
    assert set(cfg.standard.group_paths) == {"Room", "Room/Furniture", "Lights"}
    tree = structure_to_list(cfg.standard)
    names = {g["name"] for g in tree}
    assert names == {"Room", "Lights"}
    room = next(g for g in tree if g["name"] == "Room")
    assert room["children"][0]["name"] == "Furniture"


def test_unknown_rule_type_survives_load():
    cfg = load_config({"schema": 2, "rules": [{"type": "future_thing"}]})
    assert cfg.rules.rules == []
    assert len(cfg.rules.warnings) == 1
