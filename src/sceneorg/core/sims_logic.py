from __future__ import annotations

from dataclasses import dataclass, field


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
        }


def is_active_hidden(hit: SimHit) -> bool:
    return bool(hit.enabled) and hit.hidden


def is_unbaked(hit: SimHit) -> bool:
    return hit.enabled is not False and hit.cached is False


def is_disabled_leftover(hit: SimHit) -> bool:
    return hit.enabled is False


def compute_findings(hits: list) -> dict:
    return {
        "active_hidden": [h.to_dict() for h in hits if is_active_hidden(h)],
        "unbaked": [h.to_dict() for h in hits if is_unbaked(h)],
        "disabled_leftovers": [h.to_dict() for h in hits if is_disabled_leftover(h)],
    }


def summarize(hits: list) -> dict:
    by_kind: dict = {}
    for h in hits:
        by_kind[h.kind] = by_kind.get(h.kind, 0) + 1
    return {
        "total": len(hits),
        "by_kind": by_kind,
        "active_hidden": sum(1 for h in hits if is_active_hidden(h)),
        "unbaked": sum(1 for h in hits if is_unbaked(h)),
        "disabled": sum(1 for h in hits if is_disabled_leftover(h)),
    }


def scan_result(hits: list) -> dict:
    return {
        "ok": True,
        "hits": [h.to_dict() for h in hits],
        "findings": compute_findings(hits),
        "summary": summarize(hits),
    }
