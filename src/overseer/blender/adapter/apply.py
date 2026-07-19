"""ApplyOps - rename / reparent / assign-collection / revert for Blender.

STUB: implemented by a dedicated subagent. Reference: cinema/adapter/apply.py.
Blender undo model: perform all edits, then ONE ``self.doc.undo_push(msg)`` (no
per-object AddUndo). Record ``self.last_changes`` items in the SAME schema the
C4D apply.py uses so the shared core/journal.py + revert work unchanged.

Required methods (called by blender/webapi.py):
  rename_object(guid, new_name) -> bool
  apply_renames(list[ops.RenameOp]) -> int
  apply_reparents(list[ops.ReparentOp]) -> int
  apply_layers(list[ops.LayerOp]) -> int
  revert(items: list[dict]) -> {"reverted", "missing", "results"}
"""
from __future__ import annotations


class ApplyOps:

    def rename_object(self, guid, new_name: str) -> bool:
        self.last_changes = []
        return False

    def apply_renames(self, renames) -> int:
        self.last_changes = []
        return 0

    def apply_reparents(self, reparents) -> int:
        self.last_changes = []
        return 0

    def apply_layers(self, layerops) -> int:
        self.last_changes = []
        return 0

    def revert(self, items) -> dict:
        return {"reverted": 0, "missing": len(list(items or [])),
                "results": []}
