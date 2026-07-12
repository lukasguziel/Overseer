from sceneorg.naming import translate


def test_object_name_is_split_into_its_words():
    assert translate.translatable_words("body_rear_wing_part_usm.1") == [
        "body", "rear", "wing", "part", "usm"]


def test_camel_case_and_digits_do_not_hide_words():
    assert translate.translatable_words("RearWing02") == ["rearwing"]
    assert translate.translatable_words("wing_02") == ["wing"]
    # Single letters are indices/axes, not words.
    assert translate.translatable_words("wing_a_x") == ["wing"]


def test_rebuild_keeps_separators_numbers_and_unknown_codes():
    mapping = {"body": "nadwozie", "rear": "tylny", "wing": "skrzydlo",
               "part": "czesc"}
    new, changed = translate.rebuild_with("body_rear_wing_part_usm.1", mapping)
    # Separators, the unknown code and the index survive untouched.
    assert new == "nadwozie_tylny_skrzydlo_czesc_usm.1"
    assert len(changed) == 4


def test_rebuild_matches_the_casing_of_each_word():
    mapping = {"body": "nadwozie", "wing": "skrzydlo"}
    assert translate.rebuild_with("Body_WING", mapping)[0] == "Nadwozie_SKRZYDLO"


def test_words_without_a_translation_are_left_alone():
    new, changed = translate.rebuild_with("body_usm", {"body": "nadwozie"})
    assert new == "nadwozie_usm"
    assert changed == [("body", "nadwozie")]


def test_a_word_that_translates_to_itself_is_not_a_change():
    new, changed = translate.rebuild_with("part_01", {"part": "part"})
    assert new == "part_01"
    assert changed == []


def test_rebuilding_is_idempotent():
    mapping = {"body": "nadwozie"}
    once, _ = translate.rebuild_with("body_01", mapping)
    twice, changed = translate.rebuild_with(once, mapping)
    assert twice == once
    assert changed == []
