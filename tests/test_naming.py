import pytest

from sceneorg import naming
from sceneorg.naming import Casing


@pytest.mark.parametrize("name,expected", [
    ("LIGHT_KEY_01", Casing.UPPER_SNAKE),
    ("light_key_01", Casing.LOWER_SNAKE),
    ("lightKey", Casing.CAMEL),
    ("LightKey", Casing.PASCAL),
    ("Light Key", Casing.SPACED),
    ("light-key", Casing.KEBAB),
    ("LIGHT", Casing.UPPER),
    ("light", Casing.LOWER),
    ("Light", Casing.CAPITALIZED),
    ("", Casing.EMPTY),
])
def test_detect_casing(name, expected):
    assert naming.detect_casing(name) == expected


@pytest.mark.parametrize("name,tokens", [
    ("LIGHT_KEY_01", ["light", "key"]),
    ("lightKey", ["light", "key"]),
    ("Stuhl 02", ["stuhl"]),
    ("wall-north", ["wall", "north"]),
    ("Camera.Main", ["camera", "main"]),
])
def test_tokenize(name, tokens):
    assert naming.tokenize(name) == tokens


@pytest.mark.parametrize("name,base,num", [
    ("Chair 01", "Chair", 1),
    ("Chair_02", "Chair", 2),
    ("Chair-3", "Chair", 3),
    ("Chair", "Chair", None),
    ("07", "07", None),  # pure number stays unchanged
])
def test_split_trailing_number(name, base, num):
    assert naming.split_trailing_number(name) == (base, num)


def test_detect_language():
    de = {"stuhl", "licht"}
    en = {"chair", "light"}
    assert naming.detect_language("Stuhl_01", de, en) == naming.LANG_DE
    assert naming.detect_language("Chair_01", de, en) == naming.LANG_EN
    assert naming.detect_language("XYZ", de, en) == naming.LANG_UNKNOWN
    # umlaut tips the scale towards German
    assert naming.detect_language("Küche", de, en) == naming.LANG_DE
