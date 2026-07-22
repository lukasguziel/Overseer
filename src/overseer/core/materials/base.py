from __future__ import annotations

from abc import abstractmethod

from ..hostapi.items import ItemsBase


class MaterialsBase(ItemsBase):
    """The materials area: the shared workflow lives here, a host subclasses
    and overrides only the ``get_*``/``set_*`` primitives that read or write
    its own material system."""

    @abstractmethod
    def scan_materials(self, include_hidden=False, accepted=None) -> dict: ...

    @abstractmethod
    def focus_material(self, name: str) -> dict: ...

    @abstractmethod
    def delete_material(self, name: str, include_hidden=False) -> int: ...

    @abstractmethod
    def delete_unused_materials(self, include_hidden=False,
                                accepted=None) -> int: ...
