import pytest

from sceneorg.convention import NamingConvention
from sceneorg.naming import LANG_DE, LANG_EN, Casing


def test_pascal_english_translation():
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=2)
    assert conv.normalize("stuhl_01") == "Chair01"
    assert conv.normalize("KAMERA MAIN") == "CameraMain"
    assert conv.normalize("wand-nord") == "WallNord"  # 'nord' unbekannt -> bleibt


def test_lower_snake_with_number_padding():
    conv = NamingConvention(style=Casing.LOWER_SNAKE, language=None, number_pad=3)
    assert conv.normalize("LightKey 1") == "light_key_001"
    assert conv.normalize("Table") == "table"


def test_upper_snake():
    conv = NamingConvention(style=Casing.UPPER_SNAKE, language=None, number_pad=2)
    assert conv.normalize("light key 5") == "LIGHT_KEY_05"


def test_kebab_case():
    conv = NamingConvention(style=Casing.KEBAB, language=None, number_pad=2)
    assert conv.normalize("LightKey 1") == "light-key-01"
    assert conv.normalize("Table") == "table"


def test_camel_case_german_target():
    conv = NamingConvention(style=Casing.CAMEL, language=LANG_DE, number_pad=0)
    assert conv.normalize("Chair_Table") == "stuhlTisch"


def test_no_padding_keeps_plain_number():
    conv = NamingConvention(style=Casing.PASCAL, language=None, number_pad=0)
    assert conv.normalize("chair 7") == "Chair7"


def test_pure_number_or_empty_unchanged():
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN)
    assert conv.normalize("07") == "07"
    assert conv.normalize("   ") == ""


def test_propose_and_compliance():
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=2)
    p = conv.propose("stuhl_01")
    assert p.old == "stuhl_01" and p.new == "Chair01" and p.changed
    assert conv.is_compliant("Chair01")
    assert not conv.is_compliant("stuhl_01")


@pytest.mark.parametrize("style", [
    Casing.PASCAL, Casing.CAMEL, Casing.LOWER_SNAKE, Casing.UPPER_SNAKE, Casing.KEBAB,
])
@pytest.mark.parametrize("name", ["stuhl_01", "KAMERA MAIN", "wand-nord", "Chair 7", "light"])
def test_normalize_is_idempotent(style, name):
    conv = NamingConvention(style=style, language=LANG_EN, number_pad=2)
    once = conv.normalize(name)
    assert conv.normalize(once) == once


def test_invalid_style_rejected():
    # SPACED ist kein erzeugbarer Ziel-Stil
    with pytest.raises(ValueError):
        NamingConvention(style=Casing.SPACED)
