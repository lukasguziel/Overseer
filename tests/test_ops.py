from sceneorg import model, ops
from sceneorg.convention import NamingConvention
from sceneorg.naming import LANG_EN, Casing


def test_plan_renames_only_nonconforming(sample_tree):
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=2)
    renames = ops.plan_renames(sample_tree, conv)
    mapping = {r.old_name: r.new_name for r in renames}
    # "Table" ist schon konform -> nicht enthalten
    assert "Table" not in mapping
    # gemischte Namen werden normalisiert
    assert mapping["LIGHT_KEY"] == "LightKey"
    assert mapping["Stuhl_01"] == "Chair01"
    assert mapping["KAMERA MAIN"] == "CameraMain"


def test_plan_reparents_tidy_only_collects_loose(std, sample_tree):
    # Default tidy=True: nur wirklich lose Objekte einsammeln.
    reparents = ops.plan_reparents(sample_tree, std)
    moves = {r.name: (r.from_group, r.to_group) for r in reparents}
    assert moves["KAMERA MAIN"][1] == "Cameras"        # lose an der Wurzel -> einsammeln
    assert "Sofa" not in moves                          # steckt in Exterior -> in Ruhe lassen
    assert "Table" not in moves
    assert "LIGHT_KEY" not in moves


def test_plan_reparents_aggressive_moves_from_wrong_group(std, sample_tree):
    # tidy=False: zerlegt auch bestehende (falsche) Gruppen.
    reparents = ops.plan_reparents(sample_tree, std, tidy=False)
    moves = {r.name: (r.from_group, r.to_group) for r in reparents}
    assert moves["KAMERA MAIN"][1] == "Cameras"
    assert moves["Sofa"] == ("Exterior", "Furniture")


def test_plan_layers_by_type_and_category(std, sample_tree):
    layers = ops.plan_layers(sample_tree)
    by = {op_.name: op_.layer for op_ in layers}
    assert by["LIGHT_KEY"] == "Lights"
    assert by["light_fill"] == "Lights"
    assert by["KAMERA MAIN"] == "Cameras"
    # Meshes/Nulls bekommen keinen Layer
    assert "Table" not in by
    assert "Furniture" not in by


def test_plan_renames_stable_guids(sample_tree):
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN)
    renames = ops.plan_renames(sample_tree, conv)
    for r in renames:
        assert sample_tree.find(r.guid) is not None


def _null_with(children):
    parent = model.SceneNode("Group", category=model.CAT_NULL, guid=100)
    for c in children:
        parent.add_child(c)
    return model.SceneTree(roots=[parent])


def test_collision_safe_renames_unique_per_parent():
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=2)
    tree = _null_with([
        model.SceneNode("stuhl", category=model.CAT_MESH, guid=1),
        model.SceneNode("Stuhl", category=model.CAT_MESH, guid=2),
        model.SceneNode("STUHL", category=model.CAT_MESH, guid=3),
    ])
    renames = ops.plan_renames(tree, conv)
    new_names = {r.guid: r.new_name for r in renames}
    # alle drei wuerden zu "Chair" -> muessen eindeutig werden
    assert set(new_names.values()) == {"Chair", "Chair01", "Chair02"}


def test_scope_limits_renames():
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN)
    tree = _null_with([
        model.SceneNode("stuhl", category=model.CAT_MESH, guid=1),
        model.SceneNode("tisch", category=model.CAT_MESH, guid=2),
    ])
    renames = ops.plan_renames(tree, conv, scope={1})
    assert [r.guid for r in renames] == [1]


def test_type_prefix_applied_and_idempotent():
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=0)
    prefixes = {"light": "LGT_"}
    tree = _null_with([model.SceneNode("key light", category=model.CAT_LIGHT, guid=1)])
    renames = ops.plan_renames(tree, conv, prefixes=prefixes)
    assert renames[0].new_name == "LGT_KeyLight"
    # zweiter Lauf auf dem bereits praefixierten Namen -> keine Aenderung
    tree2 = _null_with([model.SceneNode("LGT_KeyLight", category=model.CAT_LIGHT, guid=1)])
    assert ops.plan_renames(tree2, conv, prefixes=prefixes) == []


def test_safety_filter_blocks_generator_child(std):
    # Mesh liegt unter einem Generator (Kategorie 'other'), nicht unter einer Null
    gen = model.SceneNode("Cloner", category=model.CAT_OTHER, guid=10)
    chair = model.SceneNode("Chair_01", category=model.CAT_MESH, guid=11)
    gen.add_child(chair)
    tree = model.SceneTree(roots=[gen])
    assert not ops.is_safe_to_reparent(chair)
    assert ops.plan_reparents(tree, std, safe_only=True) == []
    assert len(ops.plan_reparents(tree, std, safe_only=False)) == 1
