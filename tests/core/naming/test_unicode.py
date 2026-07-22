import pytest

from overseer.core.naming.casing import Casing
from overseer.core.naming.convention import TARGET_STYLES, NamingConvention

ACCENTED = ["Étagère_01", "Stůl_2", "Кресло_3"]


@pytest.mark.parametrize("keep_specials", [True, False])
def test_accented_words_are_not_mangled_or_dropped(keep_specials):
    # setup: French/Czech/Cyrillic object names -- the plugin ships dictionary
    # packs for these languages, so their letters must be words, not "specials"
    conv = NamingConvention(style=Casing.PASCAL, language=None, number_pad=2,
                            keep_specials=keep_specials)

    # do it
    out = [conv.normalize(name) for name in ACCENTED]

    # postcondition
    assert out == ["Étagère01", "Stůl02", "Кресло03"]


def test_umlaut_names_keep_working():
    # setup
    conv = NamingConvention(style=Casing.LOWER_SNAKE, language=None, number_pad=2)

    # postcondition
    assert conv.normalize("Möbel_2") == "möbel_02"
    assert conv.normalize("Küche Schrank") == "küche_schrank"


@pytest.mark.parametrize("style", TARGET_STYLES)
def test_accented_normalize_is_idempotent(style):
    # setup
    conv = NamingConvention(style=style, language=None, number_pad=2)

    # do it
    once = [conv.normalize(n) for n in ACCENTED]
    twice = [conv.normalize(n) for n in once]

    # postcondition
    assert once == twice
