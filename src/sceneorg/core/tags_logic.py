from __future__ import annotations

import math

DEFAULT_PHONG_ANGLE_DEG = 40.0


def deg_from_rad(rad: float) -> float:
    return round(math.degrees(rad), 1)


def dominant_angle(counts: dict) -> float | None:
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
