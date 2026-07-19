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


def test_blender_audits_are_concrete_audit_instances():
    # Each area's audit is a per-area Audit subclass exposing a ready AUDIT
    # instance; a missing host primitive would leave abstractmethods and fail
    # to instantiate. (Blender audits import without bpy.)
    import importlib

    from overseer.core.hostapi import Audit

    for area in ("tags", "generators", "sims", "perf", "files"):
        mod = importlib.import_module("overseer.blender.audit_" + area)
        assert mod.AUDIT is not None, area
        assert isinstance(mod.AUDIT, Audit), area
        assert type(mod.AUDIT).__abstractmethods__ == frozenset(), area
