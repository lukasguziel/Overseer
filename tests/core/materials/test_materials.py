from overseer.core.materials import logic
from overseer.core.materials.logic import is_internal_material


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


def test_scan_result_shapes_the_materials_summary():
    # setup: more missing rows than the payload cap
    missing = [{"material": "M%d" % i, "file": "t.png"} for i in range(60)]

    # do it
    out = logic.scan_result(9, ["Old", "Temp"], ["Temp"], ["Kept"],
                            {"Kept", "Also"}, missing)

    # postcondition: deletable derives from unused, missing capped at 50
    assert out["total"] == 9 and out["deletable_count"] == 2
    assert out["accepted_all"] == ["Also", "Kept"]
    assert len(out["missing"]) == 50 and out["missing_textures"] == 60
