from sceneorg.core import model
from sceneorg.structure.standard import default_standard


def test_default_standard_only_categories():
    # Placeholder/test rules removed: the default only knows Cameras + Lights
    assert set(default_standard().group_names) == {"Cameras", "Lights"}


def test_target_group_by_category(std):
    cam = model.SceneNode("Cam1", category=model.CAT_CAMERA)
    light = model.SceneNode("L1", category=model.CAT_LIGHT)
    assert std.target_group_for(cam) == "Cameras"
    assert std.target_group_for(light) == "Lights"


def test_target_group_by_keyword(std):
    chair = model.SceneNode("Stuhl_01", category=model.CAT_MESH)
    chair_en = model.SceneNode("Chair_01", category=model.CAT_MESH)
    wall = model.SceneNode("Wall_North", category=model.CAT_MESH)
    tree = model.SceneNode("Tree_01", category=model.CAT_MESH)
    assert std.target_group_for(chair_en) == "Furniture"
    assert std.target_group_for(wall) == "Interior"
    assert std.target_group_for(tree) == "Exterior"
    # German 'stuhl' is internally translated to 'chair' -> Furniture
    assert std.target_group_for(chair) == "Furniture"
    assert std.target_group_for(model.SceneNode("Baum_02")) == "Exterior"


def test_canonical_group_recognizes_alias(std):
    assert std.canonical_group("Moebel") == "Furniture"
    assert std.canonical_group("Lichter") == "Lights"
    assert std.canonical_group("Furniture") == "Furniture"
    assert std.canonical_group("Unbekannt") is None


def test_existing_alias_group_counts_as_correct(std):
    moebel = model.SceneNode("Moebel", category=model.CAT_NULL)
    moebel.add_child(model.SceneNode("Chair_01", category=model.CAT_MESH, guid=1))
    tree = model.SceneTree(roots=[moebel])
    report = std.evaluate(tree)
    assert report.misplaced == []


def test_nested_group_container_counts_as_correct(std):
    # Nested: Scene(root, not a group) > Lights > Interior > light.
    # Previously reported as misplaced (top_group == 'Scene'), now correct.
    scene = model.SceneNode("Scene", category=model.CAT_NULL, guid=1)
    lights = model.SceneNode("Lights", category=model.CAT_NULL, guid=2)
    zone = model.SceneNode("Cluster_A", category=model.CAT_NULL, guid=3)
    lamp = model.SceneNode("Key_Light", category=model.CAT_LIGHT, guid=4)
    scene.add_child(lights)
    lights.add_child(zone)
    zone.add_child(lamp)
    tree = model.SceneTree(roots=[scene])
    report = std.evaluate(tree)
    assert report.misplaced == []
    assert std.enclosing_group(lamp) == "Lights"
    assert std.enclosing_group(zone) == "Lights"


def test_loose_object_under_non_group_root_is_misplaced(std):
    # Light directly under 'Scene' (not a group container) -> loose -> misplaced.
    scene = model.SceneNode("Scene", category=model.CAT_NULL, guid=1)
    lamp = model.SceneNode("Ceiling_Light", category=model.CAT_LIGHT, guid=2)
    scene.add_child(lamp)
    tree = model.SceneTree(roots=[scene])
    report = std.evaluate(tree)
    assert {f.name for f in report.misplaced} == {"Ceiling_Light"}
    assert std.enclosing_group(lamp) is None


def test_priority_categories_win_over_keywords(std):
    n = model.SceneNode("table_cam", category=model.CAT_CAMERA)
    assert std.target_group_for(n) == "Cameras"


def test_evaluate_finds_misplaced(std, sample_tree):
    report = std.evaluate(sample_tree)
    names_misplaced = {f.name for f in report.misplaced}
    assert "KAMERA MAIN" in names_misplaced
    assert "Sofa" in names_misplaced
    assert "Baum_02" not in names_misplaced
    assert 0.0 <= report.compliance <= 1.0


def test_group_nulls_are_skipped(std, sample_tree):
    report = std.evaluate(sample_tree)
    all_names = {f.name for f in report.findings}
    assert "Lights" not in all_names
    assert "Furniture" not in all_names
