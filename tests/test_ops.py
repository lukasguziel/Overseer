from overseer.core import model, ops
from overseer.naming.casing import LANG_EN, Casing
from overseer.naming.convention import NamingConvention


def test_plan_renames_keep_list_is_left_untouched(sample_tree):
    # setup
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=2)

    # do it
    kept = ops.plan_renames(sample_tree, conv, keep={"LIGHT_KEY", "Stuhl_01"})

    # postcondition
    names = {r.old_name for r in kept}
    assert "LIGHT_KEY" not in names
    assert "Stuhl_01" not in names
    assert "KAMERA MAIN" in names


def test_plan_renames_only_nonconforming(sample_tree):
    # setup
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=2)

    # do it
    renames = ops.plan_renames(sample_tree, conv)

    # postcondition: mixed names get normalized
    mapping = {r.old_name: r.new_name for r in renames}
    assert "Table" not in mapping  # "Table" is already compliant -> not included
    assert mapping["LIGHT_KEY"] == "LightKey"
    assert mapping["Stuhl_01"] == "Chair01"
    assert mapping["KAMERA MAIN"] == "CameraMain"


def test_plan_reparents_tidy_only_collects_loose(std, sample_tree):
    # do it: default tidy=True only collects genuinely loose objects
    reparents = ops.plan_reparents(sample_tree, std)

    # postcondition
    moves = {r.name: (r.from_group, r.to_group) for r in reparents}
    assert moves["KAMERA MAIN"][1] == "Cameras"        # loose at the root -> collect
    assert "Sofa" not in moves                          # sits inside Exterior -> leave alone
    assert "Table" not in moves
    assert "LIGHT_KEY" not in moves


def test_plan_reparents_aggressive_moves_from_wrong_group(std, sample_tree):
    # do it: tidy=False also breaks up existing (wrong) groups
    reparents = ops.plan_reparents(sample_tree, std, tidy=False)

    # postcondition
    moves = {r.name: (r.from_group, r.to_group) for r in reparents}
    assert moves["KAMERA MAIN"][1] == "Cameras"
    assert moves["Sofa"] == ("Exterior", "Furniture")


def test_plan_layers_by_type_and_category(std, sample_tree):
    # do it
    layers = ops.plan_layers(sample_tree)

    # postcondition: lights/cameras get layers, meshes/nulls get none
    by = {op_.name: op_.layer for op_ in layers}
    assert by["LIGHT_KEY"] == "Lights"
    assert by["light_fill"] == "Lights"
    assert by["KAMERA MAIN"] == "Cameras"
    assert "Table" not in by
    assert "Furniture" not in by


def test_plan_renames_stable_guids(sample_tree):
    # setup
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN)

    # do it
    renames = ops.plan_renames(sample_tree, conv)

    # postcondition
    for r in renames:
        assert sample_tree.find(r.guid) is not None


def _null_with(children):
    parent = model.SceneNode("Group", category=model.CAT_NULL, guid=100)
    for c in children:
        parent.add_child(c)
    return model.SceneTree(roots=[parent])


def test_collision_safe_renames_unique_per_parent():
    # setup
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=2)
    tree = _null_with([
        model.SceneNode("stuhl", category=model.CAT_MESH, guid=1),
        model.SceneNode("Stuhl", category=model.CAT_MESH, guid=2),
        model.SceneNode("STUHL", category=model.CAT_MESH, guid=3),
    ])

    # do it
    renames = ops.plan_renames(tree, conv)

    # postcondition: all three would become "Chair" -> must be made unique
    new_names = {r.guid: r.new_name for r in renames}
    assert set(new_names.values()) == {"Chair", "Chair01", "Chair02"}


def test_scope_limits_renames():
    # setup
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN)
    tree = _null_with([
        model.SceneNode("stuhl", category=model.CAT_MESH, guid=1),
        model.SceneNode("tisch", category=model.CAT_MESH, guid=2),
    ])

    # do it
    renames = ops.plan_renames(tree, conv, scope={1})

    # postcondition
    assert [r.guid for r in renames] == [1]


def test_type_prefix_applied_and_idempotent():
    # setup
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=0)
    prefixes = {"light": "LGT_"}
    tree = _null_with([model.SceneNode("key light", category=model.CAT_LIGHT, guid=1)])

    # do it
    renames = ops.plan_renames(tree, conv, prefixes=prefixes)

    # postcondition
    assert renames[0].new_name == "LGT_KeyLight"
    tree2 = _null_with([model.SceneNode("LGT_KeyLight", category=model.CAT_LIGHT, guid=1)])
    assert ops.plan_renames(tree2, conv, prefixes=prefixes) == []  # second run on the already prefixed name -> no change


def test_safety_filter_blocks_generator_child(std):
    # setup: mesh sits under a generator (category 'other'), not under a null
    gen = model.SceneNode("Cloner", category=model.CAT_OTHER, guid=10)
    chair = model.SceneNode("Chair_01", category=model.CAT_MESH, guid=11)
    gen.add_child(chair)
    tree = model.SceneTree(roots=[gen])

    # postcondition
    assert not ops.is_safe_to_reparent(chair)
    assert ops.plan_reparents(tree, std, safe_only=True) == []
    assert len(ops.plan_reparents(tree, std, safe_only=False)) == 1
