from __future__ import annotations

from abc import abstractmethod

from ..items import ItemsBase


class LayersBase(ItemsBase):
    """The layers area: the shared workflow lives here, a host subclasses and
    overrides only the ``get_*``/``set_*`` primitives that read or write its
    own grouping primitive (C4D layers, Blender collections, ...)."""

    # -- shared workflow ----------------------------------------------------
    def scan_layers(self) -> list:
        """One row per layer handle: seed the canonical row with the reference
        counts, then merge the host's per-handle metadata over it."""
        out: list = []
        refs = self.get_layer_references()
        for handle in self.get_layer_handles():
            name = self.get_layer_name(handle)
            if name is None:
                continue
            ref = refs.get(name) or {}
            entry = self.layer_entry(name, materials=ref.get("materials", 0),
                                     tags=ref.get("tags", 0))
            entry.update(self.get_layer_meta(handle))
            out.append(entry)
        return out

    @staticmethod
    def layer_entry(name: str, color=None, solo: bool = False,
                    view: bool = True, render: bool = True,
                    locked: bool = False, materials: int = 0,
                    tags: int = 0) -> dict:
        return {"name": name, "color": color, "solo": bool(solo),
                "view": bool(view), "render": bool(render),
                "locked": bool(locked),
                "materials": int(materials), "tags": int(tags)}

    def get_layer_references(self) -> dict:
        """``{layer_name: {"materials": int, "tags": int}}`` for handles that
        other data links to. Default: none (a host whose grouping primitive
        holds no materials/tags leaves every layer at zero)."""
        return {}

    # -- primitives ---------------------------------------------------------
    @abstractmethod
    def get_layer_handles(self) -> list: ...

    @abstractmethod
    def get_layer_name(self, handle) -> str | None: ...

    @abstractmethod
    def get_layer_meta(self, handle) -> dict: ...

    @abstractmethod
    def _layer_object_counts(self) -> dict: ...

    @abstractmethod
    def delete_layer(self, name: str) -> int: ...

    @abstractmethod
    def delete_empty_layers(self, keep=None) -> int: ...

    @abstractmethod
    def set_layer_colors(self, colors: dict) -> int: ...
