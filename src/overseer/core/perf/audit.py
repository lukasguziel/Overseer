from __future__ import annotations

from abc import abstractmethod

from ..hostapi.ports import Audit


class PerfAudit(Audit):
    """Viewport rebuild-cost audit."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "perf_scan":
            return self.scan(doc, adapter, tree, payload, progress)
        if op == "perf_select":
            return self.select(doc, adapter, tree, payload)
        return {"error": "unknown perf op: %s" % op}

    @abstractmethod
    def scan(self, doc, adapter, tree, payload, progress) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...
