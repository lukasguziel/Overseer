from __future__ import annotations

# Load the hostapi package first: importing an area base directly would trip
# its eager ports<->base import cycle otherwise.
from overseer.core.layers.base import LayersBase


class _Layer:
    def __init__(self, name, meta=None):
        self.name = name
        self.meta = meta or {}


class _FakeLayers(LayersBase):
    """Minimal host: in-memory handles, base default for references."""

    def __init__(self, handles):
        self._handles = handles

    def get_layer_handles(self):
        return list(self._handles)

    def get_layer_name(self, handle):
        return handle.name

    def get_layer_meta(self, handle):
        return dict(handle.meta)

    def _layer_object_counts(self):
        return {}

    def delete_layer(self, name):
        return 0

    def delete_empty_layers(self, keep=None):
        return 0

    def set_layer_colors(self, colors):
        return 0


class _RefLayers(_FakeLayers):
    def __init__(self, handles, references):
        super().__init__(handles)
        self._references = references

    def get_layer_references(self):
        return self._references


def test_scan_layers_builds_canonical_rows_and_merges_meta():
    # setup
    handles = [
        _Layer("Geo", {"color": [0.1, 0.2, 0.3], "view": False}),
        _Layer("Props"),
    ]
    host = _FakeLayers(handles)

    # do it
    rows = host.scan_layers()

    # postcondition: the row is the canonical shape, host meta merged over it
    assert rows[0] == {"name": "Geo", "color": [0.1, 0.2, 0.3], "solo": False,
                       "view": False, "render": True, "locked": False,
                       "materials": 0, "tags": 0}
    assert rows[1] == LayersBase.layer_entry("Props")


def test_scan_layers_defaults_material_and_tag_counts_to_zero():
    # setup: no references primitive -> the base default supplies none
    host = _FakeLayers([_Layer("Loose")])

    # do it
    rows = host.scan_layers()

    # postcondition
    assert rows[0]["materials"] == 0
    assert rows[0]["tags"] == 0


def test_scan_layers_seeds_counts_from_references():
    # setup
    host = _RefLayers([_Layer("Sorting")],
                      references={"Sorting": {"materials": 4, "tags": 1}})

    # do it
    rows = host.scan_layers()

    # postcondition: reference counts seed the row before meta is merged
    assert rows[0]["materials"] == 4
    assert rows[0]["tags"] == 1


def test_scan_layers_skips_handles_without_a_name():
    # setup: a nameless handle must not produce a row
    host = _FakeLayers([_Layer(None), _Layer("Keep")])

    # do it
    rows = host.scan_layers()

    # postcondition
    assert [r["name"] for r in rows] == ["Keep"]
