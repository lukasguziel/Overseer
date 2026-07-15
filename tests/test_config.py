from overseer import config
from overseer.naming import translations
from overseer.naming.casing import LANG_DE, Casing


def test_load_defaults():
    # do it
    cfg = config.load_config()

    # postcondition
    assert cfg.convention.style == Casing.PASCAL
    assert cfg.standard.group_names  # default standard
    assert cfg.prefixes == {}


def test_load_convention_overrides():
    # do it
    cfg = config.load_config({"casing": "UPPER_SNAKE", "language": "de", "number_pad": 3})

    # postcondition
    assert cfg.convention.style == Casing.UPPER_SNAKE
    assert cfg.convention.language == LANG_DE
    assert cfg.convention.number_pad == 3


def test_load_language_null_means_no_translation():
    # do it
    cfg = config.load_config({"language": None})

    # postcondition
    assert cfg.convention.language is None


def test_custom_group_rules():
    # do it
    cfg = config.load_config({"groups": [
        {"name": "Props", "keywords": ["barstool"], "priority": 10},
        {"name": "Lights", "categories": ["light"], "priority": 100},
    ]})

    # postcondition
    assert set(cfg.standard.group_names) == {"Props", "Lights"}


def test_prefixes_loaded():
    # do it
    cfg = config.load_config({"prefixes": {"light": "LGT_", "camera": "CAM_"}})

    # postcondition
    assert cfg.prefixes["light"] == "LGT_"


def test_add_translations_extends_dictionary():
    # setup
    assert translations.to_english("barhocker") == "barhocker"

    # do it: finally block cleans up so other tests are not affected
    try:
        translations.add_translations({"Barhocker": "Barstool"})
        assert translations.to_english("barhocker") == "barstool"
        assert "barhocker" in translations.DE_WORDS
    finally:
        translations.DE_TO_EN.pop("barhocker", None)
        translations.DE_WORDS.discard("barhocker")
        translations.EN_WORDS.discard("barstool")
        translations.EN_TO_DE.pop("barstool", None)
