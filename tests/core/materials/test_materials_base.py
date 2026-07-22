from overseer.core.materials.base import MaterialsBase


class FakeMat:
    def __init__(self, name):
        self.name = name


class FakeMaterials(MaterialsBase):
    def __init__(self, mats, used_any=(), used_visible=(), missing=None,
                 raise_on_list=False):
        self._mats = [FakeMat(n) for n in mats]
        self._used_any = set(used_any)
        self._used_visible = set(used_visible)
        self._missing = missing or {}
        self._raise_on_list = raise_on_list

    def get_materials(self):
        if self._raise_on_list:
            raise RuntimeError("no material list")
        return self._mats

    def get_material_name(self, mat):
        return mat.name

    def get_material_key(self, mat):
        return mat.name

    def get_material_usage(self):
        return self._used_any, self._used_visible

    def get_missing_textures(self, mat, name):
        return [dict(row) for row in self._missing.get(name, ())]

    # host machinery not exercised by the shared scan
    def focus_material(self, name):
        return {"ok": True, "object": None}

    def delete_material(self, name, include_hidden=False):
        return 0

    def delete_unused_materials(self, include_hidden=False, accepted=None):
        return 0


def test_scan_classifies_unused_hidden_only_and_accepted():
    # setup
    host = FakeMaterials(
        ["Used", "Nowhere", "HiddenOnly", "Kept"],
        used_any={"Used", "HiddenOnly"},
        used_visible={"Used"},
    )

    # do it
    out = host.scan_materials(include_hidden=True, accepted={"Kept"})

    # postcondition: canonical scan_result shape, driven by the primitives
    assert out["total"] == 4
    assert out["unused"] == ["Nowhere", "HiddenOnly"]
    assert out["only_hidden"] == ["HiddenOnly"]
    assert out["accepted"] == ["Kept"]
    assert out["accepted_all"] == ["Kept"]
    assert out["deletable_count"] == 2


def test_hidden_only_material_excluded_when_hidden_not_included():
    # setup
    host = FakeMaterials(
        ["Nowhere", "HiddenOnly"],
        used_any={"HiddenOnly"},
        used_visible=(),
    )

    # do it
    out = host.scan_materials(include_hidden=False)

    # postcondition: a hidden-only material is not deletable
    assert out["unused"] == ["Nowhere"]
    assert out["only_hidden"] == []
    assert out["deletable_count"] == 1


def test_internal_material_is_skipped_before_missing_collection():
    # setup
    host = FakeMaterials(
        ["__temp__", "Wood"],
        missing={
            "__temp__": [{"material": "__temp__", "file": "junk.png"}],
            "Wood": [{"material": "Wood", "file": "w.png"}],
        },
    )

    # do it
    out = host.scan_materials()

    # postcondition: the internal one contributes neither a row nor a texture
    assert out["unused"] == ["Wood"]
    assert out["missing"] == [{"material": "Wood", "file": "w.png"}]
    assert out["missing_textures"] == 1


def test_is_internal_override_reshapes_classification():
    # setup
    class PrefixInternal(FakeMaterials):
        def is_internal(self, name):
            return name.startswith("TMP_") or super().is_internal(name)

    host = PrefixInternal(["TMP_scratch", "Real"])

    # do it
    out = host.scan_materials()

    # postcondition: the overridden primitive hides the prefixed material
    assert out["unused"] == ["Real"]


def test_scan_returns_empty_envelope_when_materials_unavailable():
    # setup
    host = FakeMaterials(["Whatever"], raise_on_list=True)

    # do it
    out = host.scan_materials()

    # postcondition: the try/except envelope yields a zeroed result
    assert out["total"] == 0
    assert out["unused"] == []
    assert out["missing_textures"] == 0
