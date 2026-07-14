from sceneorg.core.materials_logic import is_internal_material


def test_octane_temp_material_is_internal():
    # postcondition: the Octane clipboard/preview helper is plugin machinery
    assert is_internal_material("__octanetemp__") is True


def test_dunder_names_are_internal():
    # postcondition: the shared plugin convention, not just one renderer
    assert is_internal_material("__rs_preview__") is True
    assert is_internal_material("  __octanetemp__  ") is True


def test_artist_materials_are_not_internal():
    # postcondition: normal names, underscores included, stay visible
    assert is_internal_material("Wood_Walnut") is False
    assert is_internal_material("_shadow") is False
    assert is_internal_material("__") is False
    assert is_internal_material("") is False
    assert is_internal_material(None) is False
