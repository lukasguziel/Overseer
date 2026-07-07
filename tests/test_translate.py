from sceneorg import model, translate
from sceneorg.translations import add_translations


def setup_module(_):
    # Szenen-Vokabular, das der Produkt-Default evtl. noch nicht kennt.
    add_translations({"arbeitsplatte": "countertop", "lehne": "backrest"})


def test_translate_preserves_upper_snake():
    new, words = translate.translate_preserving("ARBEITSPLATTE_01")
    assert new == "COUNTERTOP_01"
    assert words == [("ARBEITSPLATTE", "COUNTERTOP")]


def test_translate_preserves_capitalized_and_mixed():
    new, _ = translate.translate_preserving("Stuhl Lehne")
    assert new == "Chair Backrest"


def test_translate_only_flags_translatable():
    # rein englischer Name -> keine Aenderung, keine Woerter
    new, words = translate.translate_preserving("Kitchen_Table_02")
    assert words == []
    assert new == "Kitchen_Table_02"


def test_plan_translations_filters_and_scopes():
    root = model.SceneNode("Root", category=model.CAT_NULL, guid=0)
    root.add_child(model.SceneNode("STUHL", category=model.CAT_MESH, guid=1))
    root.add_child(model.SceneNode("Table", category=model.CAT_MESH, guid=2))
    root.add_child(model.SceneNode("ARBEITSPLATTE", category=model.CAT_MESH, guid=3))
    tree = model.SceneTree(roots=[root])

    props = translate.plan_translations(tree)
    by = {p.guid: p.new for p in props}
    assert by == {1: "CHAIR", 3: "COUNTERTOP"}   # 'Table' schon englisch

    scoped = translate.plan_translations(tree, scope={3})
    assert [p.guid for p in scoped] == [3]
