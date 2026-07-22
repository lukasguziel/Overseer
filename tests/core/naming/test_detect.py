from overseer.core.naming import detect
from overseer.core.naming.casing import LANG_DE, LANG_EN, Casing


def test_detect_dominant_upper_snake():
    # setup
    names = ["LIGHT_KEY_01", "LIGHT_FILL_02", "CAM_MAIN_01", "Freeform"]

    # do it
    res = detect.detect_convention(names)

    # postcondition
    assert res.style == Casing.UPPER_SNAKE
    assert res.confidence > 0.5


def test_detect_pascal_from_capitalized_and_pascal():
    # setup
    names = ["Chair", "Table", "LightKey", "SofaLeft"]

    # do it
    res = detect.detect_convention(names)

    # postcondition
    assert res.style == Casing.PASCAL


def test_detect_kebab():
    # setup
    names = ["light-key", "wall-north", "floor-main"]

    # do it
    res = detect.detect_convention(names)

    # postcondition
    assert res.style == Casing.KEBAB
    assert res.confidence == 1.0


def test_detect_language_german():
    # setup
    names = ["Stuhl_01", "Tisch", "Küche", "Wand"]

    # do it
    res = detect.detect_convention(names)

    # postcondition
    assert res.language == LANG_DE


def test_detect_language_english():
    # setup
    names = ["Chair", "Table", "Wall", "Floor"]

    # do it
    res = detect.detect_convention(names)

    # postcondition
    assert res.language == LANG_EN


def test_detect_number_pad():
    # postcondition
    assert detect.detect_number_pad(["Chair_01", "Table_02", "Lamp_03"]) == 2
    assert detect.detect_number_pad(["Chair_001", "Table_014"]) == 3
    assert detect.detect_number_pad(["Chair_1", "Table_2"]) == 0
    assert detect.detect_number_pad(["Chair", "Table"]) == 0


def test_detect_empty_names_safe():
    # do it
    res = detect.detect_convention(["", "   ", None])

    # postcondition
    assert res.style == Casing.PASCAL  # sensible default
    assert res.confidence == 0.0
