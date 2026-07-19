"""overseer.core.hostapi - the host-abstraction layer (ports & adapters).

Pure: no ``c4d``, no ``bpy``. Defines the ports every 3D host implements so the
web UI, the op logic and all per-area domain logic can be shared across hosts
(Cinema 4D, Blender, and future ones). See docs/ai/hostapi.md.
"""
from __future__ import annotations

from .ports import Audit, HostContext, SceneAdapter, SceneHost

__all__ = ["SceneHost", "SceneAdapter", "Audit", "HostContext"]
