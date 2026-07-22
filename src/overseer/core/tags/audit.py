from __future__ import annotations

from abc import abstractmethod

from ..hostapi.ports import Audit


class TagsAudit(Audit):
    """Object-attachment audit. Fully host-specific reads, so the base only
    owns the op dispatch + the always-on tab (has_any default True)."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "tags_scan":
            return self.scan(doc, adapter, tree, progress)
        if op == "tags_add_phong":
            return self.add_phong(doc, adapter, tree, payload)
        if op == "tags_set_phong_angle":
            return self.set_phong_angle(doc, adapter, tree, payload)
        if op == "tags_delete_duplicates":
            return self.delete_duplicates(doc, adapter, tree, payload)
        if op == "tags_select":
            return self.select(doc, adapter, tree, payload)
        return {"error": "unknown tags op: %s" % op}

    @abstractmethod
    def scan(self, doc, adapter, tree, progress) -> dict: ...

    @abstractmethod
    def add_phong(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def set_phong_angle(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def delete_duplicates(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...
