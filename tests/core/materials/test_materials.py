from overseer.core.materials.base import MaterialsBase


def test_octane_temp_material_is_internal():
    # postcondition: the Octane clipboard/preview helper is plugin machinery
    assert MaterialsBase.is_internal("__octanetemp__") is True


def test_dunder_names_are_internal():
    # postcondition: the shared plugin convention, not just one renderer
    assert MaterialsBase.is_internal("__rs_preview__") is True
    assert MaterialsBase.is_internal("  __octanetemp__  ") is True


def test_artist_materials_are_not_internal():
    # postcondition: normal names, underscores included, stay visible
    assert MaterialsBase.is_internal("Wood_Walnut") is False
    assert MaterialsBase.is_internal("_shadow") is False
    assert MaterialsBase.is_internal("__") is False
    assert MaterialsBase.is_internal("") is False
    assert MaterialsBase.is_internal(None) is False


def test_scan_result_shapes_the_materials_summary():
    # setup: more missing rows than the payload cap
    missing = [{"material": "M%d" % i, "file": "t.png"} for i in range(60)]

    # do it
    out = MaterialsBase.scan_result(9, ["Old", "Temp"], ["Temp"], ["Kept"],
                            {"Kept", "Also"}, missing)

    # postcondition: deletable derives from unused, missing capped at 50
    assert out["total"] == 9 and out["deletable_count"] == 2
    assert out["accepted_all"] == ["Also", "Kept"]
    assert len(out["missing"]) == 50 and out["missing_textures"] == 60
