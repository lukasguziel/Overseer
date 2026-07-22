from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass, field

from ..hostapi.ports import Audit


@dataclass
class SimHit:
    guid: int
    object: str
    carrier: str
    kind: str
    label: str
    enabled: bool | None = None
    cached: bool | None = None
    hidden: bool = False
    notes: list = field(default_factory=list)
    # Per-object attachment index (disambiguates rows sharing (guid, kind);
    # the frontend keys rows + set_enabled targets on it). -1 = object-level.
    index: int = -1

    def to_dict(self) -> dict:
        return {
            "guid": self.guid,
            "object": self.object,
            "carrier": self.carrier,
            "kind": self.kind,
            "label": self.label,
            "enabled": self.enabled,
            "cached": self.cached,
            "hidden": self.hidden,
            "notes": list(self.notes),
            "index": self.index,
        }


class SimsAudit(Audit):
    """Simulation audit. The base owns the whole scan workflow: collect the
    host's sims into normalized ``SimHit`` objects, then shape the result via
    the shared findings/summary helpers (identical for every host). Hosts
    implement only ``collect`` / ``select`` / ``set_enabled`` / ``has_any``."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "sims_scan":
            hits = self.collect(doc, adapter, tree, progress)
            return self.scan_result(hits)
        if op == "sims_select":
            return self.select(doc, adapter, payload)
        if op == "sims_set_enabled":
            return self.set_enabled(doc, adapter, payload)
        return {"error": "unknown sims op: %s" % op}

    # -- findings ------------------------------------------------------------
    @staticmethod
    def is_active_hidden(hit: SimHit) -> bool:
        return bool(hit.enabled) and hit.hidden

    @staticmethod
    def is_unbaked(hit: SimHit) -> bool:
        return hit.enabled is not False and hit.cached is False

    @staticmethod
    def is_disabled_leftover(hit: SimHit) -> bool:
        return hit.enabled is False

    @staticmethod
    def compute_findings(hits: list) -> dict:
        return {
            "active_hidden": [h.to_dict() for h in hits
                              if SimsAudit.is_active_hidden(h)],
            "unbaked": [h.to_dict() for h in hits if SimsAudit.is_unbaked(h)],
            "disabled_leftovers": [h.to_dict() for h in hits
                                   if SimsAudit.is_disabled_leftover(h)],
        }

    @staticmethod
    def summarize(hits: list) -> dict:
        by_kind: dict = {}
        for h in hits:
            by_kind[h.kind] = by_kind.get(h.kind, 0) + 1
        return {
            "total": len(hits),
            "by_kind": by_kind,
            "active_hidden": sum(1 for h in hits
                                 if SimsAudit.is_active_hidden(h)),
            "unbaked": sum(1 for h in hits if SimsAudit.is_unbaked(h)),
            "disabled": sum(1 for h in hits
                            if SimsAudit.is_disabled_leftover(h)),
        }

    @staticmethod
    def scan_result(hits: list) -> dict:
        return {
            "ok": True,
            "hits": [h.to_dict() for h in hits],
            "findings": SimsAudit.compute_findings(hits),
            "summary": SimsAudit.summarize(hits),
        }

    # -- host primitives -----------------------------------------------------
    @abstractmethod
    def has_any(self, adapter, tree) -> bool: ...

    @abstractmethod
    def collect(self, doc, adapter, tree, progress) -> list: ...

    @abstractmethod
    def select(self, doc, adapter, payload) -> dict: ...

    @abstractmethod
    def set_enabled(self, doc, adapter, payload) -> dict: ...
