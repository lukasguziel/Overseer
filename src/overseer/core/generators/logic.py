from __future__ import annotations


def _hashable(value):
    if isinstance(value, list):
        return ("__list__", tuple(value))
    return (type(value).__name__, value)


def value_distribution(values):
    order = []
    index = {}
    for v in values:
        key = _hashable(v)
        pos = index.get(key)
        if pos is None:
            index[key] = len(order)
            order.append({"value": v, "count": 1})
        else:
            order[pos]["count"] += 1
    order.sort(key=lambda d: -d["count"])
    return order


def dominant_value(distribution):
    return distribution[0]["value"] if distribution else None


def is_uniform(distribution):
    return len(distribution) <= 1


def summarize(entries):
    values = [e["value"] for e in entries]
    dist = value_distribution(values)
    dominant = dominant_value(dist)
    return {
        "values": entries,
        "distribution": dist,
        "uniform": is_uniform(dist),
        "dominant": dominant,
        "outliers": [e for e in entries
                     if _hashable(e["value"]) != _hashable(dominant)],
    }


def value_entry(guid, name, value):
    return {"guid": guid, "name": name, "value": value}


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


def type_row(key, label, type_id, count, params):
    return {"key": key, "label": label, "type_id": type_id,
            "count": count, "params": params}


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
