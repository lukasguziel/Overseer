from __future__ import annotations

from abc import abstractmethod

from ..hostapi.ports import Audit


class GeneratorsAudit(Audit):
    """Generator/modifier settings audit. The base owns the op dispatch, the
    value summaries and the result shapes; a host implements only the read/
    apply primitives and calls the shared helpers via ``self``."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "gens_scan":
            return self.scan(doc, adapter, tree, progress)
        if op == "gens_apply":
            return self.apply(doc, adapter, tree, payload)
        if op == "gens_select":
            return self.select(doc, adapter, tree, payload)
        return {"error": "unknown gens op: %s" % op}

    # -- value summaries -----------------------------------------------------
    @staticmethod
    def _hashable(value):
        if isinstance(value, list):
            return ("__list__", tuple(value))
        return (type(value).__name__, value)

    @staticmethod
    def value_distribution(values):
        order = []
        index = {}
        for v in values:
            key = GeneratorsAudit._hashable(v)
            pos = index.get(key)
            if pos is None:
                index[key] = len(order)
                order.append({"value": v, "count": 1})
            else:
                order[pos]["count"] += 1
        order.sort(key=lambda d: -d["count"])
        return order

    @staticmethod
    def dominant_value(distribution):
        return distribution[0]["value"] if distribution else None

    @staticmethod
    def is_uniform(distribution):
        return len(distribution) <= 1

    @staticmethod
    def summarize(entries):
        values = [e["value"] for e in entries]
        dist = GeneratorsAudit.value_distribution(values)
        dominant = GeneratorsAudit.dominant_value(dist)
        return {
            "values": entries,
            "distribution": dist,
            "uniform": GeneratorsAudit.is_uniform(dist),
            "dominant": dominant,
            "outliers": [e for e in entries
                         if GeneratorsAudit._hashable(e["value"])
                         != GeneratorsAudit._hashable(dominant)],
        }

    # -- row shapes ----------------------------------------------------------
    @staticmethod
    def value_entry(guid, name, value):
        return {"guid": guid, "name": name, "value": value}

    @staticmethod
    def param_row(key, label, kind, choices, summary):
        return {
            "key": key, "label": label, "kind": kind,
            "choices": choices,
            "values": summary["values"],
            "distribution": summary["distribution"],
            "uniform": summary["uniform"],
            "dominant": summary["dominant"],
            "outliers": summary["outliers"],
        }

    @staticmethod
    def type_row(key, label, type_id, count, params):
        return {"key": key, "label": label, "type_id": type_id,
                "count": count, "params": params}

    @staticmethod
    def scan_result(types_out, total_gens, non_uniform_params):
        types_out = sorted(types_out, key=lambda t: -t["count"])
        return {
            "ok": True,
            "types": types_out,
            "summary": {
                "total_generators": total_gens,
                "types_found": len(types_out),
                "non_uniform_params": non_uniform_params,
            },
        }

    # -- host primitives -----------------------------------------------------
    @abstractmethod
    def has_any(self, adapter, tree) -> bool: ...

    @abstractmethod
    def scan(self, doc, adapter, tree, progress) -> dict: ...

    @abstractmethod
    def apply(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...
