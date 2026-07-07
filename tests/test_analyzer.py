from sceneorg import model
from sceneorg.analyzer import SceneAnalyzer


def test_analyze_counts(sample_tree):
    report = SceneAnalyzer().analyze(sample_tree, file_name="test.c4d")
    assert report.file == "test.c4d"
    assert report.object_count == len(sample_tree.all_nodes())
    assert report.categories.get(model.CAT_LIGHT) == 2
    assert report.categories.get(model.CAT_CAMERA) == 1


def test_analyze_type_stats(sample_tree):
    report = SceneAnalyzer().analyze(sample_tree)
    # Typ-Statistik summiert sich auf die Objektzahl
    assert sum(report.types.values()) == report.object_count
    # 3 Container-Nulls (Lights, Furniture, Exterior) im Sample
    assert report.types.get("Null") == 3
    assert report.max_depth >= 1


def test_analyze_casing_and_language(sample_tree):
    report = SceneAnalyzer().analyze(sample_tree)
    # gemischte Casings vorhanden
    assert "UPPER_SNAKE" in report.casing      # LIGHT_KEY
    assert sum(report.casing.values()) == report.object_count
    assert sum(report.language.values()) == report.object_count


def test_analyze_groups_and_structure(std, sample_tree):
    report = SceneAnalyzer(std).analyze(sample_tree)
    assert report.lights_by_group.get("Lights") == 2
    # lose Kamera liegt unter sich selbst als Top-Gruppe
    assert report.cameras_by_group.get("KAMERA MAIN") == 1
    assert 0.0 <= report.structure_compliance <= 1.0
    misplaced_names = {m["name"] for m in report.misplaced}
    assert "Sofa" in misplaced_names


def test_to_dict_serializable(sample_tree):
    import json
    report = SceneAnalyzer().analyze(sample_tree)
    s = json.dumps(report.to_dict())
    assert "structure_compliance" in s
