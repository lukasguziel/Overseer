from __future__ import annotations

from .scene import model

UPDATE_REPO = "lukasguziel/overseer"

CATEGORY_LAYERS = {
    model.CAT_LIGHT: "Lights",
    model.CAT_CAMERA: "Cameras",
}

TYPE_LAYERS = {
    "Instance": "Proxies",
}

DEFAULT_LAYER_SCHEME = {
    "categories": dict(CATEGORY_LAYERS),
    "types": dict(TYPE_LAYERS),
}

LAYER_COLORS = {
    "Lights": (0.98, 0.75, 0.14),
    "Cameras": (0.22, 0.74, 0.97),
    "Proxies": (0.69, 0.48, 1.0),
    "Splines": (0.55, 0.60, 0.70),
}
