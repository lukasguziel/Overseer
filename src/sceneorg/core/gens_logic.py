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
