from sceneorg import config, translations
from sceneorg.naming import LANG_DE, Casing


def test_load_defaults():
    cfg = config.load_config()
    assert cfg.convention.style == Casing.PASCAL
    assert cfg.standard.group_names  # default standard
    assert cfg.prefixes == {}


def test_load_convention_overrides():
    cfg = config.load_config({"casing": "UPPER_SNAKE", "language": "de", "number_pad": 3})
    assert cfg.convention.style == Casing.UPPER_SNAKE
    assert cfg.convention.language == LANG_DE
    assert cfg.convention.number_pad == 3


def test_load_language_null_means_no_translation():
    cfg = config.load_config({"language": None})
    assert cfg.convention.language is None


def test_custom_group_rules():
    cfg = config.load_config({"groups": [
        {"name": "Props", "keywords": ["barstool"], "priority": 10},
        {"name": "Lights", "categories": ["light"], "priority": 100},
    ]})
    assert set(cfg.standard.group_names) == {"Props", "Lights"}


def test_prefixes_loaded():
    cfg = config.load_config({"prefixes": {"light": "LGT_", "camera": "CAM_"}})
    assert cfg.prefixes["light"] == "LGT_"


def test_add_translations_extends_dictionary():
    # Aufraeumen, damit andere Tests nicht beeinflusst werden
    assert translations.to_english("barhocker") == "barhocker"
    try:
        translations.add_translations({"Barhocker": "Barstool"})
        assert translations.to_english("barhocker") == "barstool"
        assert "barhocker" in translations.DE_WORDS
    finally:
        translations.DE_TO_EN.pop("barhocker", None)
        translations.DE_WORDS.discard("barhocker")
        translations.EN_WORDS.discard("barstool")
        translations.EN_TO_DE.pop("barstool", None)
