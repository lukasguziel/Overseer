from overseer import config
from overseer.core import defaults
from overseer.core.naming import translations
from overseer.core.naming.casing import LANG_DE, Casing


def test_load_defaults():
    # do it
    cfg = config.load_config()

    # postcondition
    assert cfg.convention.style == Casing.PASCAL
    assert cfg.keeps == {s: [] for s in ("naming", "translate", "layers", "materials", "files", "textures")}


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


def test_default_config_carries_server_settings():
    # postcondition: the port default has exactly one source of truth
    assert config.DEFAULT_CONFIG["port"] == defaults.DEFAULT_PORT
    assert config.DEFAULT_CONFIG["listen_lan"] is False
    assert set(config.MACHINE_LOCAL_KEYS) == {"port", "listen_lan"}


def test_migrate_carries_machine_local_keys():
    # setup
    data = {"schema": 1, "prefixes": {"light": "LGT_"},
            "port": 9000, "listen_lan": True}

    # do it
    out = config.migrate_config(data)

    # postcondition: server settings survive migration, retired keys are dropped
    assert out["port"] == 9000
    assert out["listen_lan"] is True
    assert out["schema"] == config.CONFIG_SCHEMA_VERSION
    assert "prefixes" not in out


def test_migrate_drops_retired_keys():
    # setup: a config written by the old rule-engine/preset era
    data = {"schema": 3, "casing": "camelCase", "structure": [{"name": "Cameras"}],
            "rules": [{"type": "prefix"}], "graph": {"nodes": []}, "preset": "old"}

    # do it
    out = config.migrate_config(data)

    # postcondition: settings survive, the retired era is gone
    assert out["casing"] == "camelCase"
    for key in ("structure", "rules", "graph", "preset"):
        assert key not in out


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
