from sceneorg.config import load_config
from sceneorg.naming.casing import Casing
from sceneorg.structure.graph import graph_from_structure


def test_load_config_survives_malformed_values():
    # setup: a hand-edited config with an invalid casing, a text number_pad and
    # a nameless structure group
    data = {
        "schema": 3,
        "casing": "pascal",
        "number_pad": "two",
        "structure": [{"categories": ["camera"], "priority": "high"}],
    }

    # do it
    cfg = load_config(data)

    # postcondition: defaults instead of a crash that would brick every request
    assert cfg.convention.style == Casing.PASCAL
    assert cfg.convention.number_pad == 2
    assert cfg.standard.group_names == ["Group"]


def test_load_config_survives_broken_schema_and_rules():
    # do it
    cfg = load_config({"schema": "v3", "rules": ["oops", {"type": "prefix"}]})

    # postcondition
    assert cfg.rules.rules == []
    assert len(cfg.rules.warnings) == 2


def test_graph_rows_do_not_overlap_with_many_categories():
    # setup: four categories stack past the default row pitch
    structure = [
        {"name": "Wide", "categories": ["mesh", "spline", "light", "camera"]},
        {"name": "Next", "categories": ["null"]},
    ]

    # do it
    g = graph_from_structure(structure)

    # postcondition: the next group starts below the last category node
    cats = [n for n in g["nodes"] if n["type"] == "category"]
    groups = [n for n in g["nodes"] if n["type"] == "group"]
    lowest_cat_of_first = max(c["position"]["y"] for c in cats[:4])
    assert groups[1]["position"]["y"] > lowest_cat_of_first
