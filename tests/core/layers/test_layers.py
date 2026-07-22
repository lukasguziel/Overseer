from overseer.core.layers import report as layers
from overseer.core.organize import ops
from overseer.core.scene import model


def _node(name, guid, layer=None, cat=model.CAT_MESH, children=None):
    n = model.SceneNode(name=name, category=cat, guid=guid, layer=layer)
    for c in (children or []):
        n.add_child(c)
    return n


def test_layer_is_empty_only_without_objects_materials_and_tags():
    # setup
    meta = [
        {"name": "Geo", "materials": 0, "tags": 0},
        {"name": "MatsOnly", "materials": 3, "tags": 0},
        {"name": "TagsOnly", "materials": 0, "tags": 2},
        {"name": "Truly Empty", "materials": 0, "tags": 0},
    ]

    # do it
    rep = layers.build_layer_report(meta, object_counts={"Geo": 5})

    # postcondition: a layer counts as empty only when nothing references it
    by = {ly["name"]: ly for ly in rep["layers"]}
    assert by["Geo"]["empty"] is False
    assert by["MatsOnly"]["empty"] is False           # materials keep it alive
    assert by["TagsOnly"]["empty"] is False           # tags keep it alive
    assert by["Truly Empty"]["empty"] is True
    assert rep["empty_layers"] == 1


def test_hidden_only_layer_is_not_empty_under_visible_perspective():
    # setup: PARTICLES holds only hidden objects — 0 visible, 13 in total
    meta = [
        {"name": "PARTICLES", "materials": 0, "tags": 0},
        {"name": "Truly Empty", "materials": 0, "tags": 0},
    ]

    # do it: visible-only object_counts, full counts via all_object_counts
    rep = layers.build_layer_report(
        meta, object_counts={},
        all_object_counts={"PARTICLES": 13})

    # postcondition: hidden objects keep the layer alive; the surfaced
    # objects_all lets the UI explain why
    by = {ly["name"]: ly for ly in rep["layers"]}
    assert by["PARTICLES"]["empty"] is False
    assert by["PARTICLES"]["objects"] == 0
    assert by["PARTICLES"]["objects_all"] == 13
    assert by["Truly Empty"]["empty"] is True
    assert rep["empty_layers"] == 1


def test_layer_report_surfaces_material_and_tag_counts():
    # setup
    meta = [{"name": "Sorting", "materials": 4, "tags": 1}]

    # do it
    rep = layers.build_layer_report(meta, object_counts={"Sorting": 2},
                                    poly_counts={"Sorting": 900})

    # postcondition
    ly = rep["layers"][0]
    assert ly["objects"] == 2
    assert ly["materials"] == 4
    assert ly["tags"] == 1
    assert ly["polys"] == 900


def test_ancestor_layer_suggestion_for_unassigned_object():
    # setup: a null on "Interior", a child mesh with no layer
    child = _node("Chair", 2)
    parent = _node("Room", 1, layer="Interior", cat=model.CAT_NULL,
                   children=[child])
    tree = model.SceneTree(roots=[parent])

    # do it
    sugg = ops.plan_layer_suggestions(tree)

    # postcondition: only the layerless child gets the ancestor's layer
    by = {o.name: o.layer for o in sugg}
    assert by == {"Chair": "Interior"}


def test_no_suggestion_when_no_ancestor_has_a_layer():
    # setup
    child = _node("Loose", 2)
    parent = _node("Group", 1, cat=model.CAT_NULL, children=[child])
    tree = model.SceneTree(roots=[parent])

    # do it
    sugg = ops.plan_layer_suggestions(tree)

    # postcondition
    assert sugg == []


def test_suggestion_skips_kept_names():
    # setup
    child = _node("Chair", 2)
    parent = _node("Room", 1, layer="Interior", cat=model.CAT_NULL,
                   children=[child])
    tree = model.SceneTree(roots=[parent])

    # do it
    sugg = ops.plan_layer_suggestions(tree, keep={"Chair"})

    # postcondition
    assert sugg == []


def test_mismatch_finding_flags_child_on_different_layer():
    # setup: parent on layer A, one child on layer B, one matching child
    diff = _node("Lamp", 2, layer="Props")
    same = _node("Wall", 3, layer="Shell")
    parent = _node("Shell", 1, layer="Shell", cat=model.CAT_NULL,
                   children=[diff, same])
    tree = model.SceneTree(roots=[parent])

    # do it
    found = layers.find_layer_mismatches(tree)

    # postcondition: only the differing child is reported (informational)
    assert [f.name for f in found] == ["Lamp"]
    f = found[0]
    assert f.parent_layer == "Shell"
    assert f.child_layer == "Props"


def test_mismatch_finding_ignores_unassigned_and_kept():
    # setup: layerless child is not a mismatch; a kept one is filtered out
    layerless = _node("Ghost", 2)
    kept = _node("Lamp", 3, layer="Props")
    parent = _node("Shell", 1, layer="Shell", cat=model.CAT_NULL,
                   children=[layerless, kept])
    tree = model.SceneTree(roots=[parent])

    # do it
    found = layers.find_layer_mismatches(tree, keep={"Lamp"})

    # postcondition
    assert found == []


def test_layer_entry_carries_the_canonical_row_shape():
    # do it
    default = layers.layer_entry("Props")
    filled = layers.layer_entry("Lights", solo=True, view=False,
                                materials=3, tags=2)

    # postcondition: exactly the keys both hosts ship, host fills only extras
    assert default == {"name": "Props", "color": None, "solo": False,
                       "view": True, "render": True, "locked": False,
                       "materials": 0, "tags": 0}
    assert filled["solo"] is True and filled["view"] is False
    assert filled["materials"] == 3 and filled["tags"] == 2
