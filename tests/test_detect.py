from sceneorg import detect
from sceneorg.naming import LANG_DE, LANG_EN, Casing


def test_detect_dominant_upper_snake():
    names = ["LIGHT_KEY_01", "LIGHT_FILL_02", "CAM_MAIN_01", "Freeform"]
    res = detect.detect_convention(names)
    assert res.style == Casing.UPPER_SNAKE
    assert res.confidence > 0.5


def test_detect_pascal_from_capitalized_and_pascal():
    names = ["Chair", "Table", "LightKey", "SofaLeft"]
    res = detect.detect_convention(names)
    assert res.style == Casing.PASCAL


def test_detect_kebab():
    names = ["light-key", "wall-north", "floor-main"]
    res = detect.detect_convention(names)
    assert res.style == Casing.KEBAB
    assert res.confidence == 1.0


def test_detect_language_german():
    names = ["Stuhl_01", "Tisch", "Küche", "Wand"]
    res = detect.detect_convention(names)
    assert res.language == LANG_DE


def test_detect_language_english():
    names = ["Chair", "Table", "Wall", "Floor"]
    res = detect.detect_convention(names)
    assert res.language == LANG_EN


def test_detect_number_pad():
    assert detect.detect_number_pad(["Chair_01", "Table_02", "Lamp_03"]) == 2
    assert detect.detect_number_pad(["Chair_001", "Table_014"]) == 3
    assert detect.detect_number_pad(["Chair_1", "Table_2"]) == 0
    assert detect.detect_number_pad(["Chair", "Table"]) == 0


def test_detect_empty_names_safe():
    res = detect.detect_convention(["", "   ", None])
    assert res.style == Casing.PASCAL  # sensible default
    assert res.confidence == 0.0
