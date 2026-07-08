from __future__ import annotations

import c4d

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
