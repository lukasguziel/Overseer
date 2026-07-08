from sceneorg.core import model
from sceneorg.structure.standard import default_standard


def test_default_standard_only_categories():
    # postcondition: placeholder/test rules removed -- the default only knows Cameras + Lights
    assert set(default_standard().group_names) == {"Cameras", "Lights"}


def test_target_group_by_category(std):
    # setup
    cam = model.SceneNode("Cam1", category=model.CAT_CAMERA)
    light = model.SceneNode("L1", category=model.CAT_LIGHT)

    # postcondition
    assert std.target_group_for(cam) == "Cameras"
    assert std.target_group_for(light) == "Lights"


def test_target_group_by_keyword(std):
    # setup
    chair = model.SceneNode("Stuhl_01", category=model.CAT_MESH)
    chair_en = model.SceneNode("Chair_01", category=model.CAT_MESH)
    wall = model.SceneNode("Wall_North", category=model.CAT_MESH)
    tree = model.SceneNode("Tree_01", category=model.CAT_MESH)

    # postcondition
    assert std.target_group_for(chair_en) == "Furniture"
    assert std.target_group_for(wall) == "Interior"
    assert std.target_group_for(tree) == "Exterior"
    assert std.target_group_for(chair) == "Furniture"  # 'stuhl' translated to 'chair'
    assert std.target_group_for(model.SceneNode("Baum_02")) == "Exterior"


def test_canonical_group_recognizes_alias(std):
    # postcondition
    assert std.canonical_group("Moebel") == "Furniture"
    assert std.canonical_group("Lichter") == "Lights"
    assert std.canonical_group("Furniture") == "Furniture"
    assert std.canonical_group("Unbekannt") is None


def test_existing_alias_group_counts_as_correct(std):
    # setup
    moebel = model.SceneNode("Moebel", category=model.CAT_NULL)
    moebel.add_child(model.SceneNode("Chair_01", category=model.CAT_MESH, guid=1))
    tree = model.SceneTree(roots=[moebel])

    # do it
    report = std.evaluate(tree)

    # postcondition
    assert report.misplaced == []


def test_nested_group_container_counts_as_correct(std):
    # setup: Scene (root, not a group) > Lights > zone > light; previously
    # reported as misplaced (top_group == 'Scene'), now correct
    scene = model.SceneNode("Scene", category=model.CAT_NULL, guid=1)
    lights = model.SceneNode("Lights", category=model.CAT_NULL, guid=2)
    zone = model.SceneNode("Cluster_A", category=model.CAT_NULL, guid=3)
    lamp = model.SceneNode("Key_Light", category=model.CAT_LIGHT, guid=4)
    scene.add_child(lights)
    lights.add_child(zone)
    zone.add_child(lamp)
    tree = model.SceneTree(roots=[scene])

    # do it
    report = std.evaluate(tree)

    # postcondition
    assert report.misplaced == []
    assert std.enclosing_group(lamp) == "Lights"
    assert std.enclosing_group(zone) == "Lights"


def test_loose_object_under_non_group_root_is_misplaced(std):
    # setup: light directly under 'Scene' (not a group container) -> loose -> misplaced
    scene = model.SceneNode("Scene", category=model.CAT_NULL, guid=1)
    lamp = model.SceneNode("Ceiling_Light", category=model.CAT_LIGHT, guid=2)
    scene.add_child(lamp)
    tree = model.SceneTree(roots=[scene])

    # do it
    report = std.evaluate(tree)

    # postcondition
    assert {f.name for f in report.misplaced} == {"Ceiling_Light"}
    assert std.enclosing_group(lamp) is None


def test_priority_categories_win_over_keywords(std):
    # setup
    n = model.SceneNode("table_cam", category=model.CAT_CAMERA)

    # postcondition
    assert std.target_group_for(n) == "Cameras"


def test_evaluate_finds_misplaced(std, sample_tree):
    # do it
    report = std.evaluate(sample_tree)

    # postcondition
    names_misplaced = {f.name for f in report.misplaced}
    assert "KAMERA MAIN" in names_misplaced
    assert "Sofa" in names_misplaced
    assert "Baum_02" not in names_misplaced
    assert 0.0 <= report.compliance <= 1.0


def test_group_nulls_are_skipped(std, sample_tree):
    # do it
    report = std.evaluate(sample_tree)

    # postcondition
    all_names = {f.name for f in report.findings}
    assert "Lights" not in all_names
    assert "Furniture" not in all_names
