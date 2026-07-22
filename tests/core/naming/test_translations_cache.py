import importlib
import sys


def test_bulk_parse_survives_module_purge():
    # setup
    import overseer.core.naming.translations as t1
    de_first = t1.BULK["de"]
    unique_first = t1.UNIQUE_LANG
    assert de_first, "bundled de dictionary should load"

    # do it
    del sys.modules["overseer.core.naming.translations"]
    import overseer.core.naming.translations as t2

    # postcondition
    assert t2.BULK["de"] is de_first
    assert t2.UNIQUE_LANG is unique_first


def test_cache_invalidates_on_file_key_change():
    # setup
    import overseer.core.naming.translations as t
    cache = t._data_cache()
    key, payload = cache["de"]
    cache["de"] = ((key[0], key[1] + 1, key[2]), payload)

    # do it
    t2 = importlib.reload(t)

    # postcondition: the tampered key is gone and the TSV was parsed again
    assert cache["de"][0] == key
    assert t2.BULK["de"] is not payload[0]  # a fresh dict, not the cached one
    assert t2.BULK["de"] == payload[0]


def test_lookup_still_works_after_reload():
    # setup
    import overseer.core.naming.translations as t
    del sys.modules["overseer.core.naming.translations"]
    import overseer.core.naming.translations as t  # noqa: F811

    # postcondition
    assert t.to_english("stuhl") == "chair"
    assert t.lookup_en("tisch", "de") == "table"
