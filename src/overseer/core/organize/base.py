from __future__ import annotations

from abc import abstractmethod

from ..items import ItemsBase
from .journal import change_item


class OrganizeBase(ItemsBase):
    """Applying planned operations (rename/reparent/layer) and reverting
    journal items. The shared rename workflow and the change log live here; a
    host implements only the primitives that resolve and mutate its own
    objects plus its undo bracket, and overrides the workflows that genuinely
    differ (Blender's two-phase rename, each host's group/layer resolution and
    revert)."""

    # -- object primitives (a host reads/writes its own objects) -----------
    @abstractmethod
    def resolve_object(self, guid: int): ...

    @abstractmethod
    def get_object_name(self, obj) -> str: ...

    @abstractmethod
    def set_object_name(self, obj, name: str) -> bool: ...

    @abstractmethod
    def object_sid(self, obj) -> int: ...

    # -- undo bracket (C4D: Start/AddUndo/End + EventAdd; Blender: one push
    #    + tag_redraw, so begin_edit/touch are no-ops there) ----------------
    @abstractmethod
    def begin_edit(self) -> None: ...

    @abstractmethod
    def touch(self, obj, kind: str) -> None: ...

    @abstractmethod
    def end_edit(self, label: str) -> None: ...

    @abstractmethod
    def notify(self) -> None: ...

    # -- shared change log --------------------------------------------------
    def _log_change(self, obj, field: str, before, after) -> None:
        self.last_changes.append(change_item(
            self.object_sid(obj), self.get_object_name(obj), field,
            before, after))

    # -- shared rename workflow --------------------------------------------
    def rename_object(self, guid: int, new_name: str) -> bool:
        self.last_changes = []
        obj = self.resolve_object(guid)
        if obj is None:
            return False
        before = self.get_object_name(obj)
        if before == new_name:
            return True
        self.begin_edit()
        self.touch(obj, "name")
        if not self.set_object_name(obj, new_name):
            return False
        self._log_change(obj, "name", before, self.get_object_name(obj))
        self.end_edit("Overseer: rename")
        self.notify()
        return True

    def apply_renames(self, renames) -> int:
        self.last_changes = []
        renames = list(renames or [])
        if not renames:
            return 0
        self.begin_edit()
        count = 0
        for op in renames:
            obj = self.resolve_object(op.guid)
            if obj is None:
                continue
            before = self.get_object_name(obj)
            self.touch(obj, "name")
            self.set_object_name(obj, op.new_name)
            self._log_change(obj, "name", before, self.get_object_name(obj))
            count += 1
        self.end_edit("Overseer: rename %d" % count)
        self.notify()
        return count

    # -- host-specific workflows (kept as overrides) -----------------------
    @abstractmethod
    def apply_reparents(self, reparents) -> int: ...

    @abstractmethod
    def apply_layers(self, layerops) -> int: ...

    @abstractmethod
    def revert(self, items) -> dict: ...
