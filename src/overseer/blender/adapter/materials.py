"""MaterialOps - material scan/focus/delete for Blender.

STUB: implemented by a dedicated subagent. Reference: cinema/adapter/materials.py
and core/materials_logic.py. Material identity = ``name_full`` (duplicate base
names exist as ``.001``). Skip ``__``-prefixed internal materials. Mirror the
C4D return-dict shapes exactly.
"""
from __future__ import annotations


class MaterialOps:

    def scan_materials(self, include_hidden=False, accepted=None) -> dict:
        return {"materials": [], "unused": [], "summary": {}}

    def focus_material(self, name: str) -> dict:
        return {"found": False}

    def delete_material(self, name: str, include_hidden=False) -> int:
        return 0

    def delete_unused_materials(self, include_hidden=False, accepted=None) -> int:
        return 0
