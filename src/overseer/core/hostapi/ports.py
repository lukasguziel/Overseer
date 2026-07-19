"""The ports: abstract base classes every 3D host implements.

Pure (no host SDK). A host package (``cinema/``, ``blender/``, future ones)
subclasses these; the shared webapi is written against them. Method return
shapes are the NORMALIZED domain dicts documented here — identical across hosts
so the frozen frontend never sees a host difference.

Adding a host = implement ``SceneHost`` + ``SceneAdapter`` (+ per-area
``Audit``) + a ``HostContext``. The abstract methods are the checklist: a host
that forgets one cannot be instantiated.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .. import model


class SceneHost(ABC):
    """The normalized "document" — C4D's ``BaseDocument`` / Blender's active
    scene. Read-only host state + the mutation plumbing the webapi needs; no
    area-specific logic lives here."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Document file name (or "(unsaved)")."""

    @property
    @abstractmethod
    def path(self) -> str:
        """Directory containing the document ("" if unsaved)."""

    @abstractmethod
    def dirty(self) -> int:
        """An O(1) edit token: bumps on data edits, NOT on selection/camera.
        The cross-request scene cache is keyed on it."""

    @abstractmethod
    def selection_token(self) -> tuple:
        """``(token:int, names:list[str] (<=6), count:int)`` for the current
        host selection."""

    @abstractmethod
    def undo_push(self, message: str = "Overseer") -> None:
        """Close one undo step covering the just-applied edits."""

    @abstractmethod
    def objects(self) -> list:
        """All host objects in the document (any hierarchy depth)."""

    @abstractmethod
    def roots(self) -> list:
        """Top-level host objects, in stable order."""

    def tag_redraw(self) -> None:  # noqa: B027 - optional hook, default no-op
        """Best-effort viewport/UI refresh after a mutation (optional)."""

    def status(self, text: str | None) -> None:  # noqa: B027 - optional hook
        """Best-effort host status-bar text (optional)."""


class SceneAdapter(ABC):
    """The doc<->``SceneTree`` bridge and every scene mutation, grouped by
    area. The one place host-specific bodies live; each returns the normalized
    dict documented on the C4D reference. Hosts keep composing these from
    mixins — this ABC only makes the contract explicit and enforced."""

    # -- tree ---------------------------------------------------------------
    @abstractmethod
    def build_tree(self, progress=None) -> model.SceneTree: ...

    @abstractmethod
    def selected_guids(self, include_children: bool = True) -> set: ...

    @abstractmethod
    def focus(self, guid: int) -> bool: ...

    # -- naming / structure -------------------------------------------------
    @abstractmethod
    def rename_object(self, guid: int, new_name: str) -> bool: ...

    @abstractmethod
    def apply_renames(self, renames) -> int: ...

    @abstractmethod
    def apply_reparents(self, reparents) -> int: ...

    @abstractmethod
    def revert(self, items) -> dict: ...

    # -- layers -------------------------------------------------------------
    @abstractmethod
    def apply_layers(self, layerops) -> int: ...

    @abstractmethod
    def scan_layers(self) -> list: ...

    @abstractmethod
    def _layer_object_counts(self) -> dict: ...

    @abstractmethod
    def delete_layer(self, name: str) -> int: ...

    @abstractmethod
    def delete_empty_layers(self, keep=None) -> int: ...

    @abstractmethod
    def set_layer_colors(self, colors: dict) -> int: ...

    # -- materials ----------------------------------------------------------
    @abstractmethod
    def scan_materials(self, include_hidden=False, accepted=None) -> dict: ...

    @abstractmethod
    def focus_material(self, name: str) -> dict: ...

    @abstractmethod
    def delete_material(self, name: str, include_hidden=False) -> int: ...

    @abstractmethod
    def delete_unused_materials(self, include_hidden=False,
                                accepted=None) -> int: ...

    # -- previews -----------------------------------------------------------
    @abstractmethod
    def material_previews(self, names, size=48, progress=None) -> dict: ...

    @abstractmethod
    def texture_previews(self, paths, size=40, progress=None) -> dict: ...

    # -- textures -----------------------------------------------------------
    @abstractmethod
    def scan_textures(self, include_hidden=False, accepted=None) -> dict: ...

    @abstractmethod
    def make_textures_relative(self, materials=None) -> dict: ...

    @abstractmethod
    def texture_owners(self, path: str) -> dict: ...

    @abstractmethod
    def collect_textures(self, materials=None, subdir="tex", paths=None) -> dict: ...

    @abstractmethod
    def relink_textures(self, folder: str, progress=None) -> dict: ...

    @abstractmethod
    def clear_missing_textures(self, accepted=None) -> dict: ...

    @abstractmethod
    def set_texture_path(self, path: str, new_path: str, material=None) -> dict: ...

    @abstractmethod
    def texture_repath(self, paths, mode="relative", material=None) -> dict: ...

    @abstractmethod
    def texture_resize(self, paths, percent) -> dict: ...


class Audit(ABC):
    """Per-area audit port (tags / generators / sims / perf / files). The base
    routes ``op`` to a primitive and assembles the normalized result; the host
    overrides the read/apply primitives.

    Current hosts still ship audits as MODULES exposing ``handle(op, payload,
    doc, adapter, tree, progress)`` (+ ``has_any``); a module satisfies this
    port structurally. Phase 3 promotes them to subclasses."""

    @abstractmethod
    def handle(self, op: str, payload: dict, host: SceneHost,
               adapter: SceneAdapter, tree, progress) -> dict: ...

    def has_any(self, adapter: SceneAdapter, tree) -> bool:
        """Whether this area has anything to show (gates its tab)."""
        return True


class HostContext(ABC):
    """The small host-specific surface the shared webapi calls instead of
    importing a host. One instance per host; ``webapi.build_handle(ctx)`` binds
    it into that host's ``handle(payload)``."""

    # -- document + adapter -------------------------------------------------
    @abstractmethod
    def active_host(self) -> SceneHost | None:
        """The active document wrapper, or None if there is none."""

    @abstractmethod
    def make_adapter(self, host: SceneHost) -> SceneAdapter:
        """Construct this host's SceneAdapter over ``host``."""

    # -- paths --------------------------------------------------------------
    @property
    @abstractmethod
    def plugin_dir(self) -> str: ...

    @property
    @abstractmethod
    def data_dir(self) -> str: ...

    # -- progress -----------------------------------------------------------
    @abstractmethod
    def progress(self, phase, current=0, total=0, detail="") -> None: ...

    @abstractmethod
    def clear_progress(self) -> None: ...

    # -- bridge facades (for netinfo) --------------------------------------
    @abstractmethod
    def server_port(self) -> int: ...

    @abstractmethod
    def lan_enabled(self) -> bool: ...

    # -- host-specific ops --------------------------------------------------
    def type_icons(self, ids) -> dict:
        """type id -> data-URI icon (optional; default: none)."""
        return {}

    def pick_texture_path(self, payload: dict, host: SceneHost) -> dict:
        """Native file picker for a texture (optional)."""
        return {"ok": True, "cancelled": True}

    def pick_folder(self, payload: dict, host: SceneHost) -> dict:
        """Native folder picker (optional)."""
        return {"ok": True, "path": "", "cancelled": True}

    @abstractmethod
    def audit(self, prefix: str):
        """The Audit (or audit module) for ``tags``/``gens``/``sims``/``perf``/
        ``files``, or None if unknown."""
