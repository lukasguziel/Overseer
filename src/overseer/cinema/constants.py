from __future__ import annotations

import c4d

DEFAULT_PORT = 8787

UPDATE_PROFILE = {
    "asset_pattern": "Overseer-Cinema4D-*.zip",
    "payload_marker": "overseer.pyp",
    "disable_globs": ("*.pyp",),
}

RS_LIGHT_IDS = {1036751}
RS_CAMERA_IDS = {1057516}

DOC_JOURNAL_ID = 1069221

KNOWN_TYPES = {
    c4d.Onull: "Null",
    c4d.Ocamera: "Camera",
    c4d.Olight: "Light",
    c4d.Opolygon: "Mesh",
    c4d.Ospline: "Spline",
    c4d.Oinstance: "Instance",
    1018544: "MoGraph Cloner",
    1018545: "MoGraph Matrix",
    1018791: "MoGraph Fracture",
    1019268: "MoGraph Text",
}
