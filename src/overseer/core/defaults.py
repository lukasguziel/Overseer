from __future__ import annotations

from . import model

DEFAULT_PORT = 8787

UPDATE_REPO = "lukasguziel/overseer"

UPDATE_CINEMA = {
    "asset_pattern": "Overseer-Cinema4D-*.zip",
    "payload_marker": "overseer.pyp",
    "disable_globs": ("*.pyp",),
}

UPDATE_BLENDER = {
    "asset_pattern": "Overseer-Blender-*.zip",
    "payload_marker": "__init__.py",
    "disable_globs": ("blender_manifest.toml",),
}

RS_LIGHT_IDS = {1036751}
RS_CAMERA_IDS = {1057516}

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
