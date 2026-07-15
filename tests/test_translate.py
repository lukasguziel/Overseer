from overseer.core import model
from overseer.naming import translate, translations

# Scene vocabulary the product default may not know yet. add_translations writes
# into process-global dicts, so the snapshot is restored for the other modules.
_EXTRA = {"arbeitsplatte": "countertop", "lehne": "backrest"}
_SNAPSHOT: dict = {}


def setup_module(_):
    _SNAPSHOT["de_to_en"] = dict(translations.DE_TO_EN)
    _SNAPSHOT["en_to_de"] = dict(translations.EN_TO_DE)
    _SNAPSHOT["de_words"] = set(translations.DE_WORDS)
    _SNAPSHOT["en_words"] = set(translations.EN_WORDS)
    translations.add_translations(_EXTRA)


def teardown_module(_):
    for name, key in (("DE_TO_EN", "de_to_en"), ("EN_TO_DE", "en_to_de"),
                      ("DE_WORDS", "de_words"), ("EN_WORDS", "en_words")):
        container = getattr(translations, name)
        container.clear()
        container.update(_SNAPSHOT[key])


def test_translate_preserves_upper_snake():
    # do it
    new, words = translate.translate_preserving("ARBEITSPLATTE_01")

    # postcondition
    assert new == "COUNTERTOP_01"
    assert words == [("ARBEITSPLATTE", "COUNTERTOP")]


def test_translate_preserves_capitalized_and_mixed():
    # do it
    new, _ = translate.translate_preserving("Stuhl Lehne")

    # postcondition
    assert new == "Chair Backrest"


def test_translate_only_flags_translatable():
    # do it
    new, words = translate.translate_preserving("Kitchen_Table_02")

    # postcondition: purely English name -> no change, no words
    assert words == []
    assert new == "Kitchen_Table_02"


def test_ambiguous_word_not_translated_without_evidence():
    # do it: "bad", "wand", "regal" are common English words -> must stay put
    # when the name has no other German signal (the false-positive bug).
    for name in ("bad_geometry", "Magic_Wand", "regal_shelf", "BAD_01"):
        new, words = translate.translate_preserving(name)
        assert words == [], name
        assert new == name, name


def test_ambiguous_word_translated_with_german_evidence():
    # do it: umlaut elsewhere in the name is enough evidence -> now "Bad" is German
    new, _ = translate.translate_preserving("Kueche_Bad")  # 'kueche' is DE
    assert new == "Kitchen_Bathroom"
    new2, _ = translate.translate_preserving("Bad_Fliesen_Grün")  # umlaut
    assert new2.startswith("Bathroom")


def test_translate_target_german():
    # do it
    new, words = translate.translate_preserving("Chair_Table", target="de")

    # postcondition
    assert new == "Stuhl_Tisch"
    assert ("Chair", "Stuhl") in words


def test_detect_languages_summary():
    # setup: with the bundled bulk dictionary, "Root" itself detects as English
    # -- use a German container name so the intent (dominant=de) stays clear.
    root = model.SceneNode("Schrank", category=model.CAT_NULL, guid=0)
    root.add_child(model.SceneNode("STUHL", category=model.CAT_MESH, guid=1))
    root.add_child(model.SceneNode("Kitchen", category=model.CAT_MESH, guid=2))
    root.add_child(model.SceneNode("Tisch", category=model.CAT_MESH, guid=3))
    tree = model.SceneTree(roots=[root])

    # do it
    s = translate.detect_languages(tree)

    # postcondition
    assert s.total == 4
    assert s.de == 3 and s.en == 1
    assert s.dominant == "de"


def test_plan_translations_filters_and_scopes():
    # setup
    root = model.SceneNode("Root", category=model.CAT_NULL, guid=0)
    root.add_child(model.SceneNode("STUHL", category=model.CAT_MESH, guid=1))
    root.add_child(model.SceneNode("Table", category=model.CAT_MESH, guid=2))
    root.add_child(model.SceneNode("ARBEITSPLATTE", category=model.CAT_MESH, guid=3))
    tree = model.SceneTree(roots=[root])

    # do it
    props = translate.plan_translations(tree)
    scoped = translate.plan_translations(tree, scope={3})

    # postcondition
    by = {p.guid: p.new for p in props}
    assert by == {1: "CHAIR", 3: "COUNTERTOP"}   # 'Table' already English
    assert [p.guid for p in scoped] == [3]
