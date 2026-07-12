from sceneorg.naming import translate


def test_object_name_is_split_into_its_words():
    # postcondition
    assert translate.translatable_words("body_rear_wing_part_usm.1") == [
        "body", "rear", "wing", "part", "usm"]


def test_camel_case_and_digits_do_not_hide_words():
    # postcondition
    assert translate.translatable_words("RearWing02") == ["rearwing"]
    assert translate.translatable_words("wing_02") == ["wing"]
    assert translate.translatable_words("wing_a_x") == ["wing"]  # a/x are indices


def test_rebuild_keeps_separators_numbers_and_unknown_codes():
    # setup
    mapping = {"body": "nadwozie", "rear": "tylny", "wing": "skrzydlo",
               "part": "czesc"}

    # do it
    new, changed = translate.rebuild_with("body_rear_wing_part_usm.1", mapping)

    # postcondition: separators, the unknown code and the index survive untouched
    assert new == "nadwozie_tylny_skrzydlo_czesc_usm.1"
    assert len(changed) == 4


def test_rebuild_matches_the_casing_of_each_word():
    # setup
    mapping = {"body": "nadwozie", "wing": "skrzydlo"}

    # postcondition
    assert translate.rebuild_with("Body_WING", mapping)[0] == "Nadwozie_SKRZYDLO"


def test_words_without_a_translation_are_left_alone():
    # do it
    new, changed = translate.rebuild_with("body_usm", {"body": "nadwozie"})

    # postcondition
    assert new == "nadwozie_usm"
    assert changed == [("body", "nadwozie")]


def test_a_word_that_translates_to_itself_is_not_a_change():
    # do it
    new, changed = translate.rebuild_with("part_01", {"part": "part"})

    # postcondition
    assert new == "part_01"
    assert changed == []


def test_rebuilding_is_idempotent():
    # setup
    mapping = {"body": "nadwozie"}

    # do it
    once, _ = translate.rebuild_with("body_01", mapping)
    twice, changed = translate.rebuild_with(once, mapping)

    # postcondition
    assert twice == once
    assert changed == []
