"""BlenderContext - binds the Blender host into the shared op layer.

Implements ``HostContext``: the only Blender-specific surface the shared
``core.hostapi.webapi`` needs (active document, adapter factory, progress sink,
bridge facades, per-area audits, journal storage). Everything else is inherited
from the shared webapi.
"""
from __future__ import annotations

import importlib
import os

from ..core.hostapi import HostContext
from . import host as bridge
from .organize.journal import load_journal, save_journal
from .scene.adapter import SceneAdapter
from .scene.doc import BScene

# Addon root = dir containing the ``overseer`` package (3 up from this file).
_PLUGIN_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _prefs_base() -> str | None:
    try:
        import bpy
        return bpy.utils.user_resource("CONFIG")
    except Exception:
        return None


class BlenderContext(HostContext):

    def __init__(self) -> None:
        from ..core import webio
        self._plugin_dir = _PLUGIN_DIR
        self._data_dir = webio.resolve_data_dir(_PLUGIN_DIR, _prefs_base())

    # -- document + adapter -------------------------------------------------
    def active_host(self):
        return BScene.active()

    def make_adapter(self, host):
        return SceneAdapter(host)

    # -- paths --------------------------------------------------------------
    @property
    def plugin_dir(self) -> str:
        return self._plugin_dir

    @property
    def data_dir(self) -> str:
        return self._data_dir

    # -- auto-update --------------------------------------------------------
    @property
    def host_label(self) -> str:
        return "Blender"

    @property
    def update_profile(self) -> dict:
        from ..core import defaults
        return defaults.UPDATE_BLENDER

    # -- progress -----------------------------------------------------------
    def progress(self, phase, current=0, total=0, detail="") -> None:
        bridge.set_progress(phase, current, total, detail)

    def clear_progress(self) -> None:
        bridge.clear_progress()

    # -- bridge facades -----------------------------------------------------
    def server_port(self) -> int:
        return int(bridge.server_port())

    def lan_enabled(self) -> bool:
        return bool(bridge.lan_enabled())

    # -- journal ------------------------------------------------------------
    def load_journal(self, host, fallback_path: str) -> list:
        return load_journal(host, fallback_path)

    def save_journal(self, host, entries: list, fallback_path: str) -> None:
        save_journal(host, entries, fallback_path)

    # -- host-specific ops --------------------------------------------------
    def type_icons(self, ids) -> dict:
        # Blender object "types" are string enums, not numeric resource ids;
        # the tree renders fine without per-type PNGs.
        return {}

    def pick_texture_path(self, payload: dict, host) -> dict:
        # A blocking native picker isn't safely reachable from the pump timer;
        # the UI treats a cancel as a no-op.
        return {"ok": True, "cancelled": True,
                "note": "Use Blender's file browser to relink, then rescan."}

    def pick_folder(self, payload: dict, host) -> dict:
        return {"ok": True, "path": "", "cancelled": True,
                "note": "Folder picking from the web UI is not yet wired on Blender."}

    def audit(self, prefix: str):
        name = {"tags": "tags", "gens": "generators", "files": "files",
                "sims": "sims", "perf": "perf"}.get(prefix)
        if name is None:
            return None
        mod = importlib.import_module("overseer.blender." + name)
        # Audits are per-area Audit subclasses exposing a ready ``AUDIT``
        # instance; fall back to the module for any not-yet-converted area.
        return getattr(mod, "AUDIT", mod)
