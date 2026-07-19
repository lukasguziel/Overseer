"""Tree building / classification against a fake ``bpy``.

Drives the real ``BScene`` + ``SceneAdapter`` foundation over a synthetic
Blender scene: guids, hierarchy/depth, category mapping, the collection-as-layer
read, selection sets, and the ``dirty()`` fingerprint contract.
"""
from __future__ import annotations

import fakebpy
import pytest

from overseer.blender.adapter.scene import SceneAdapter
from overseer.blender.scene import BScene


@pytest.fixture
def blender_scene():
    """Build a synthetic scene, install it as ``sys.modules['bpy']`` and tear
    it down afterwards so the fake never leaks into the bpy-free suite."""
    def _factory(*args, **kwargs) -> fakebpy.FakeBpy:
        fake = fakebpy.make_scene(*args, **kwargs)
        fakebpy.install(fake)
        return fake

    yield _factory
    fakebpy.reset()

# A deliberately mixed scene: one grouped mesh under an Empty (which is also
# selected), plus a loose camera, light and curve - one object of every mapped
# category so classify() is exercised end to end.
SCENE = [
    {"name": "Rig", "type": "EMPTY", "selected": True},
    {"name": "Body", "type": "MESH", "parent": "Rig",
     "pts": 8, "polys": 6, "collection": "Props"},
    {"name": "Cam", "type": "CAMERA"},
    {"name": "Sun", "type": "LIGHT", "selected": True},
    {"name": "Path", "type": "CURVE"},
]
COLLECTIONS = ["Props"]


def _build(blender_scene):
    blender_scene(SCENE, collections=COLLECTIONS)
    doc = BScene.active()
    adapter = SceneAdapter(doc)
    tree = adapter.build_tree()
    return doc, adapter, tree


def _by_name(tree):
    return {n.name: n for n in tree.walk()}


def test_guids_are_sequential_and_dense(blender_scene):
    _doc, _adapter, tree = _build(blender_scene)

    guids = sorted(n.guid for n in tree.walk())
    assert guids == list(range(len(guids)))
    assert len(guids) == len(SCENE)


def test_hierarchy_and_depth(blender_scene):
    _doc, _adapter, tree = _build(blender_scene)
    nodes = _by_name(tree)

    # Body is parented under Rig -> depth 1 below the depth-0 roots.
    assert nodes["Rig"].depth == 0
    assert nodes["Body"].depth == 1
    assert nodes["Body"].parent is nodes["Rig"]
    assert [c.name for c in nodes["Rig"].children] == ["Body"]
    # The four parent-less objects are the roots.
    assert {r.name for r in tree.roots} == {"Rig", "Cam", "Sun", "Path"}


def test_classify_maps_every_category(blender_scene):
    _doc, _adapter, tree = _build(blender_scene)
    nodes = _by_name(tree)

    assert nodes["Sun"].category == "light"
    assert nodes["Cam"].category == "camera"
    assert nodes["Rig"].category == "null"      # EMPTY -> null
    assert nodes["Body"].category == "mesh"
    assert nodes["Path"].category == "spline"   # CURVE -> spline


def test_evaluated_geometry_is_read(blender_scene):
    _doc, _adapter, tree = _build(blender_scene)
    body = _by_name(tree)["Body"]

    assert body.point_count == 8
    assert body.poly_count == 6


def test_layer_name_reads_owning_collection(blender_scene):
    _doc, _adapter, tree = _build(blender_scene)
    nodes = _by_name(tree)

    # Body lives in the "Props" collection; the others only in the master
    # collection, which is not a layer.
    assert nodes["Body"].layer == "Props"
    assert nodes["Cam"].layer is None
    assert nodes["Rig"].layer is None


def test_selection_sets_populate_from_select_get(blender_scene):
    _doc, adapter, tree = _build(blender_scene)
    nodes = _by_name(tree)

    rig, sun, body = nodes["Rig"].guid, nodes["Sun"].guid, nodes["Body"].guid
    # Directly selected objects (select_get() -> True).
    assert adapter._selected_direct == {rig, sun}
    # The subtree scope pulls in Body as a child of the selected Rig.
    subtree = adapter.selected_guids(include_children=True)
    assert {rig, sun, body} <= subtree
    assert body not in adapter.selected_guids(include_children=False)


def test_dirty_is_stable_across_selection_but_bumps_on_edit(blender_scene):
    # dirty() is now the O(1) host edit-epoch counter (a depsgraph_update_post
    # handler advances it on real data edits). Selection changes are not
    # depsgraph updates, so they must not move it; a real edit (simulated here
    # via the same counter the handler drives) must.
    from overseer.blender import host

    fake = blender_scene(SCENE, collections=COLLECTIONS)
    doc = BScene.active()

    base = doc.dirty()

    # Changing selection must NOT move the token (the scene cache is keyed on it
    # and guids must survive a plan -> apply round trip).
    for obj in fake.data.objects:
        obj.select_set(not obj.select_get())
    assert doc.dirty() == base

    # A real data edit fires depsgraph_update_post -> the handler bumps the
    # epoch. Simulate that edit signal and confirm dirty() reflects it.
    host.bump_epoch()
    assert doc.dirty() != base
