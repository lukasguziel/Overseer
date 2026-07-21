"""Blender type/category constants (the Blender twin of cinema/constants.py)."""
from __future__ import annotations

from ..core import model

# bpy object type enum -> overseer category.
CATEGORY_BY_TYPE = {
    "LIGHT": model.CAT_LIGHT,
    "LIGHT_PROBE": model.CAT_LIGHT,
    "CAMERA": model.CAT_CAMERA,
    "EMPTY": model.CAT_NULL,
    "MESH": model.CAT_MESH,
    "CURVE": model.CAT_SPLINE,
    "SURFACE": model.CAT_SPLINE,
    "FONT": model.CAT_SPLINE,
    "CURVES": model.CAT_SPLINE,
}

# bpy object type enum -> readable label shown in the tree (parity with C4D's
# per-object type name). Object-level generators live in modifiers, so the
# object label stays the data type.
TYPE_LABELS = {
    "MESH": "Mesh",
    "CURVE": "Spline",
    "SURFACE": "NURBS Surface",
    "META": "Metaball",
    "FONT": "Text",
    "CURVES": "Hair Curves",
    "POINTCLOUD": "Point Cloud",
    "VOLUME": "Volume",
    "GPENCIL": "Grease Pencil",
    "GREASEPENCIL": "Grease Pencil",
    "ARMATURE": "Armature",
    "LATTICE": "Lattice",
    "EMPTY": "Empty",
    "LIGHT": "Light",
    "LIGHT_PROBE": "Light Probe",
    "CAMERA": "Camera",
    "SPEAKER": "Speaker",
}

# Materials whose name marks them as plugin/engine-internal (skipped by the
# unused scan and never deleted) - parity with C4D's ``__octanetemp__`` rule.
INTERNAL_MATERIAL_PREFIXES = ("__",)
