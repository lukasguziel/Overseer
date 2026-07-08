from sceneorg import config
from sceneorg.core import keeps


def test_empty_keeps_has_all_sections():
    m = keeps.empty_keeps()
    assert set(m) == set(keeps.SECTIONS)
    assert all(v == [] for v in m.values())


def test_normalize_keeps_dedupes_sorts_and_drops_unknown():
    m = keeps.normalize_keeps({"naming": ["b", "a", "b", 1], "bogus": ["x"]})
    assert m["naming"] == ["1", "a", "b"]
    assert "bogus" not in m
    assert m["materials"] == []


def test_set_section_keeps_replaces_only_that_section():
    m = keeps.set_section_keeps({"naming": ["a"]}, "layers", ["Wall", "Wall"])
    assert m["layers"] == ["Wall"]
    assert m["naming"] == ["a"]


def test_set_section_keeps_rejects_unknown_section():
    try:
        keeps.set_section_keeps(None, "nope", [])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_filter_kept_splits_and_reports_hits():
    items = [{"n": "A"}, {"n": "B"}, {"n": "A"}]
    todo, hits = keeps.filter_kept(items, {"A"}, key=lambda i: i["n"])
    assert [i["n"] for i in todo] == ["B"]
    assert hits == ["A"]


def test_migrate_v2_folds_flat_lists_into_keeps():
    out = config.migrate_config({
        "schema": 2, "keep_names": ["Sofa"], "accepted_unused": ["OldMat"],
    })
    assert out["schema"] == config.CONFIG_SCHEMA_VERSION
    assert out["keeps"]["naming"] == ["Sofa"]
    assert out["keeps"]["materials"] == ["OldMat"]
    assert "keep_names" not in out and "accepted_unused" not in out


def test_migrate_v1_to_v3_chains():
    out = config.migrate_config({
        "prefixes": {"light": "LGT_"}, "keep_names": ["Kamera"],
    })
    assert out["schema"] == config.CONFIG_SCHEMA_VERSION
    assert out["rules"][0]["type"] == "prefix"
    assert out["keeps"]["naming"] == ["Kamera"]


def test_migrate_is_idempotent():
    once = config.migrate_config({"schema": 2, "keep_names": ["A"]})
    twice = config.migrate_config(once)
    assert once == twice


def test_config_aliases_read_from_keeps():
    cfg = config.load_config({"schema": 3, "keeps": {
        "naming": ["Sofa"], "materials": ["Mat"], "structure": ["Wand"],
    }})
    assert cfg.keep_names == {"Sofa"}
    assert cfg.accepted_unused == {"Mat"}
    assert cfg.kept("structure") == {"Wand"}
    assert cfg.kept("translate") == set()
