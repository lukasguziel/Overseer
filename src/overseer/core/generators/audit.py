from __future__ import annotations

from abc import abstractmethod

from ..hostapi.ports import Audit


class GeneratorsAudit(Audit):
    """Generator/modifier settings audit."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "gens_scan":
            return self.scan(doc, adapter, tree, progress)
        if op == "gens_apply":
            return self.apply(doc, adapter, tree, payload)
        if op == "gens_select":
            return self.select(doc, adapter, tree, payload)
        return {"error": "unknown gens op: %s" % op}

    @abstractmethod
    def has_any(self, adapter, tree) -> bool: ...

    @abstractmethod
    def scan(self, doc, adapter, tree, progress) -> dict: ...

    @abstractmethod
    def apply(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...
