import pytest

from sceneorg.naming.casing import LANG_DE, LANG_EN, Casing
from sceneorg.naming.convention import NamingConvention


def test_pascal_english_translation():
    conv = NamingConvention(style=Casing.PASCAL, language=LANG_EN, number_pad=2)
    assert conv.normalize("stuhl_01") == "Chair01"
    assert conv.normalize("KAMERA MAIN") == "CameraMain"
    assert conv.normalize("wand-nord") == "WallNord"  # 'nord' unknown -> stays


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


def test_leading_and_inner_numbers_are_kept():
    conv = NamingConvention(style=Casing.UPPER_SNAKE, language=None, number_pad=2)
    assert conv.normalize("-1 Basement") == "1_BASEMENT"
    assert conv.normalize("2 Floor Kitchen") == "2_FLOOR_KITCHEN"

    pas = NamingConvention(style=Casing.PASCAL, language=None, number_pad=0)
    assert pas.normalize("-1 Basement") == "1Basement"


def test_casing_disabled_keeps_format_only_renumbers():
    conv = NamingConvention(style=Casing.PASCAL, language=None, number_pad=2,
                            apply_casing=False)
    assert conv.normalize("my_weird Name") == "my_weird Name"  # casing/separators untouched
    assert conv.normalize("Chair_5") == "Chair_05"             # only the number is padded
    assert conv.normalize("ROCK_UV_2.1") == "ROCK_UV_2.1"      # decimals left alone

    both_off = NamingConvention(style=Casing.PASCAL, language=None,
                                apply_casing=False, apply_numbering=False)
    assert both_off.normalize("Chair_5") == "Chair_5"          # nothing changes


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


def test_preserves_decimals_and_inner_numbers():
    # Naming only re-cases; it must not swallow the ".1" or reorder numbers.
    c = NamingConvention(style=Casing.UPPER_SNAKE, language=None, number_pad=2)
    assert c.normalize("ROCK_UV_2.1") == "ROCK_UV_2.1"      # already compliant
    c2 = NamingConvention(style=Casing.PASCAL, language=None, number_pad=2)
    assert c2.normalize("rock_uv_2.1") == "RockUv2.1"       # dot survives
    assert c2.is_compliant("RockUv2.1")


def test_numbering_toggle_off_keeps_numbers_verbatim():
    on = NamingConvention(style=Casing.PASCAL, language=None, number_pad=2)
    off = NamingConvention(style=Casing.PASCAL, language=None, number_pad=2,
                           apply_numbering=False)
    assert on.normalize("chair_1") == "Chair01"     # padded when on
    assert off.normalize("chair_1") == "Chair1"     # untouched when off
    assert off.normalize("chair_007") == "Chair007"  # no reformatting at all


def test_invalid_style_rejected():
    # SPACED is not a producible target style
    with pytest.raises(ValueError):
        NamingConvention(style=Casing.SPACED)
