from __future__ import annotations

from abc import abstractmethod

from ..hostapi.items import ItemsBase


class OrganizeBase(ItemsBase):
    """Applying planned operations (rename/reparent/layer) and reverting
    journal items. The shared loops live here; a host overrides only the
    primitives that resolve and mutate its own objects, plus its undo
    bracket."""

    @abstractmethod
    def rename_object(self, guid: int, new_name: str) -> bool: ...

    @abstractmethod
    def apply_renames(self, renames) -> int: ...

    @abstractmethod
    def apply_reparents(self, reparents) -> int: ...

    @abstractmethod
    def apply_layers(self, layerops) -> int: ...

    @abstractmethod
    def revert(self, items) -> dict: ...
