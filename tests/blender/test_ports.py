"""The Blender host must satisfy the hostapi ports (the shared contract).

Pure class introspection - no bpy needed. If a future edit drops a required
adapter/host method (or the port grows one a host forgot), instantiation of the
concrete class would fail with unimplemented abstractmethods; this locks it in
at import time so the regression is caught in CI without Blender.
"""
from __future__ import annotations

from overseer.blender.adapter import SceneAdapter as BlenderAdapter
from overseer.blender.scene import BScene
from overseer.core.hostapi import SceneAdapter, SceneHost


def test_bscene_implements_scenehost_port():
    assert issubclass(BScene, SceneHost)
    assert BScene.__abstractmethods__ == frozenset()


def test_blender_adapter_implements_sceneadapter_port():
    assert issubclass(BlenderAdapter, SceneAdapter)
    assert BlenderAdapter.__abstractmethods__ == frozenset()
