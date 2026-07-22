from __future__ import annotations

from abc import abstractmethod

from ..hostapi.ports import Audit
from . import logic


class SimsAudit(Audit):
    """Simulation audit. The base owns the whole scan workflow: collect the
    host's sims into normalized ``logic.SimHit`` objects, then shape the
    result via the pure ``logic.scan_result`` (identical for every host).
    Hosts implement only ``collect`` / ``select`` / ``set_enabled`` /
    ``has_any``."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "sims_scan":
            hits = self.collect(doc, adapter, tree, progress)
            return logic.scan_result(hits)
        if op == "sims_select":
            return self.select(doc, adapter, payload)
        if op == "sims_set_enabled":
            return self.set_enabled(doc, adapter, payload)
        return {"error": "unknown sims op: %s" % op}

    @abstractmethod
    def has_any(self, adapter, tree) -> bool: ...

    @abstractmethod
    def collect(self, doc, adapter, tree, progress) -> list: ...

    @abstractmethod
    def select(self, doc, adapter, payload) -> dict: ...

    @abstractmethod
    def set_enabled(self, doc, adapter, payload) -> dict: ...
