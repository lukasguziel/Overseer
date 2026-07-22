from __future__ import annotations

from abc import abstractmethod

from ..hostapi.ports import Audit


class FilesAudit(Audit):
    """External-file reference audit."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "files_scan":
            return self.scan(doc, adapter, tree, progress)
        if op == "files_make_relative":
            return self.make_relative(doc, adapter, tree, payload)
        if op == "files_select":
            return self.select(doc, adapter, tree, payload)
        if op == "files_pick_path":
            return self.pick_path(doc, adapter, tree, payload)
        if op == "files_relink":
            return self.relink(doc, adapter, tree, payload, progress)
        return {"error": "unknown files op: %s" % op}

    @abstractmethod
    def scan(self, doc, adapter, tree, progress) -> dict: ...

    @abstractmethod
    def make_relative(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def pick_path(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def relink(self, doc, adapter, tree, payload, progress) -> dict: ...
