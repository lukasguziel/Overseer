from __future__ import annotations

from abc import abstractmethod

from ..hostapi.items import ItemsBase


class LayersBase(ItemsBase):
    """The layers area: the shared workflow lives here, a host subclasses and
    overrides only the ``get_*``/``set_*`` primitives that read or write its
    own grouping primitive (C4D layers, Blender collections, ...)."""

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
