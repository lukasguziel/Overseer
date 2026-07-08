from sceneorg.core import model
from sceneorg.naming import translate
from sceneorg.naming.translations import add_translations


def setup_module(_):
    # Scene vocabulary the product default may not know yet.
    add_translations({"arbeitsplatte": "countertop", "lehne": "backrest"})


def test_translate_preserves_upper_snake():
    new, words = translate.translate_preserving("ARBEITSPLATTE_01")
    assert new == "COUNTERTOP_01"
    assert words == [("ARBEITSPLATTE", "COUNTERTOP")]


def test_translate_preserves_capitalized_and_mixed():
    new, _ = translate.translate_preserving("Stuhl Lehne")
    assert new == "Chair Backrest"


def test_translate_only_flags_translatable():
    # purely English name -> no change, no words
    new, words = translate.translate_preserving("Kitchen_Table_02")
    assert words == []
    assert new == "Kitchen_Table_02"


def test_ambiguous_word_not_translated_without_evidence():
    # "bad", "wand", "regal" are common English words -> must stay put when the
    # name has no other German signal (the false-positive bug).
    for name in ("bad_geometry", "Magic_Wand", "regal_shelf", "BAD_01"):
        new, words = translate.translate_preserving(name)
        assert words == [], name
        assert new == name, name


def test_ambiguous_word_translated_with_german_evidence():
    # Umlaut elsewhere in the name is enough evidence -> now "Bad" is German.
    new, _ = translate.translate_preserving("Kueche_Bad")  # 'kueche' is DE
    assert new == "Kitchen_Bathroom"
    new2, _ = translate.translate_preserving("Bad_Fliesen_Grün")  # umlaut
    assert new2.startswith("Bathroom")


def test_translate_target_german():
    new, words = translate.translate_preserving("Chair_Table", target="de")
    assert new == "Stuhl_Tisch"
    assert ("Chair", "Stuhl") in words


def test_detect_languages_summary():
    # NB: with the bundled bulk dictionary, "Root" itself detects as English
    # -- use a German container name so the intent (dominant=de) stays clear.
    root = model.SceneNode("Schrank", category=model.CAT_NULL, guid=0)
    root.add_child(model.SceneNode("STUHL", category=model.CAT_MESH, guid=1))
    root.add_child(model.SceneNode("Kitchen", category=model.CAT_MESH, guid=2))
    root.add_child(model.SceneNode("Tisch", category=model.CAT_MESH, guid=3))
    tree = model.SceneTree(roots=[root])
    s = translate.detect_languages(tree)
    assert s.total == 4
    assert s.de == 3 and s.en == 1
    assert s.dominant == "de"


def test_plan_translations_filters_and_scopes():
    root = model.SceneNode("Root", category=model.CAT_NULL, guid=0)
    root.add_child(model.SceneNode("STUHL", category=model.CAT_MESH, guid=1))
    root.add_child(model.SceneNode("Table", category=model.CAT_MESH, guid=2))
    root.add_child(model.SceneNode("ARBEITSPLATTE", category=model.CAT_MESH, guid=3))
    tree = model.SceneTree(roots=[root])

    props = translate.plan_translations(tree)
    by = {p.guid: p.new for p in props}
    assert by == {1: "CHAIR", 3: "COUNTERTOP"}   # 'Table' already English

    scoped = translate.plan_translations(tree, scope={3})
    assert [p.guid for p in scoped] == [3]
