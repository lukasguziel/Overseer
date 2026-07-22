from overseer.core.scene import model
from overseer.core.scene.analyzer import SceneAnalyzer


def test_analyze_counts(sample_tree):
    # do it
    report = SceneAnalyzer().analyze(sample_tree, file_name="test.c4d")

    # postcondition
    assert report.file == "test.c4d"
    assert report.object_count == len(sample_tree.all_nodes())
    assert report.categories.get(model.CAT_LIGHT) == 2
    assert report.categories.get(model.CAT_CAMERA) == 1


def test_analyze_type_stats(sample_tree):
    # do it
    report = SceneAnalyzer().analyze(sample_tree)

    # postcondition
    assert sum(report.types.values()) == report.object_count  # type stats sum to object count
    assert report.types.get("Null") == 3  # 3 container nulls (Lights, Furniture, Exterior)
    assert report.max_depth >= 1


def test_analyze_casing_and_language(sample_tree):
    # do it
    report = SceneAnalyzer().analyze(sample_tree)

    # postcondition
    assert "UPPER_SNAKE" in report.casing      # mixed casings present (LIGHT_KEY)
    assert sum(report.casing.values()) == report.object_count
    assert sum(report.language.values()) == report.object_count


def test_analyze_groups(sample_tree):
    # do it
    report = SceneAnalyzer().analyze(sample_tree)

    # postcondition
    assert report.lights_by_group.get("Lights") == 2
    assert report.cameras_by_group.get("KAMERA MAIN") == 1  # loose camera is its own top group


def test_analyze_layers():
    # setup
    a = model.SceneNode("A", category=model.CAT_MESH, guid=0, poly_count=10,
                        layer="Geo")
    b = model.SceneNode("B", category=model.CAT_MESH, guid=1, poly_count=5,
                        layer="Geo")
    c = model.SceneNode("C", category=model.CAT_LIGHT, guid=2, layer="Lights")
    d = model.SceneNode("D", category=model.CAT_MESH, guid=3)  # no layer
    tree = model.SceneTree(roots=[a, b, c, d])

    # do it
    report = SceneAnalyzer().analyze(tree)

    # postcondition: per-object layer is exposed in the node dicts (for the tree view)
    assert report.layers_by_name == {"Geo": 2, "Lights": 1}
    assert report.polys_by_layer == {"Geo": 15, "Lights": 0}
    assert report.no_layer_count == 1
    layers = {n["name"]: n["layer"] for n in report.nodes}
    assert layers == {"A": "Geo", "B": "Geo", "C": "Lights", "D": None}


def test_layers_respect_visibility_filter():
    # setup
    vis = model.SceneNode("V", category=model.CAT_MESH, guid=0, layer="Geo")
    hid = model.SceneNode("H", category=model.CAT_MESH, guid=1, layer="Geo",
                          visible=False)
    tree = model.SceneTree(roots=[vis, hid])

    # do it
    report = SceneAnalyzer().analyze(tree, include_hidden=False)

    # postcondition
    assert report.layers_by_name == {"Geo": 1}


def test_to_dict_serializable(sample_tree):
    # setup
    import json
    report = SceneAnalyzer().analyze(sample_tree)

    # do it
    s = json.dumps(report.to_dict())

    # postcondition
    assert "layers_by_name" in s
