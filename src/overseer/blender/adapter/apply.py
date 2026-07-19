"""ApplyOps - rename / reparent / assign-collection / revert for Blender.

The Blender twin of ``cinema/adapter/apply.py``. Blender's undo model groups by
*push*, not by C4D's Start/AddUndo/End: we perform ALL edits, then issue ONE
``self.doc.undo_push(msg)`` plus ``self.doc.tag_redraw()`` so the whole mutation
is a single undo step and the viewport refreshes once.

Every mutation records ``self.last_changes`` in the SAME item schema the C4D
``apply.py`` uses so the shared ``core/journal.py`` and the webapi
``_op_revert_change`` work unchanged across a hot-reload::

    {"sid": <session_uid int>, "name": <obj name at log time>,
     "field": "name"|"layer"|"parent", "before": <old>, "after": <new>}

Blender has no persistent guid, so ``revert`` re-finds a live object by its
session-stable ``session_uid`` (``sid``) first, then falls back to matching by
the recorded object name (the ``after`` name for renames, the ``name`` field
otherwise) - identical to the C4D fallback.
"""
from __future__ import annotations

from ...core.ops import LayerOp, RenameOp, ReparentOp
from .readers import stable_id


class ApplyOps:

    # -- small guarded bpy helpers -----------------------------------------
    def _safe_name(self, obj) -> str:
        try:
            return obj.name
        except Exception:
            return ""

    def _set_name(self, obj, new_name: str) -> bool:
        try:
            obj.name = new_name
            return True
        except Exception:
            return False

    def _log_change(self, obj, field: str, before, after) -> None:
        self.last_changes.append({
            "sid": stable_id(obj),
            "name": self._safe_name(obj),
            "field": field,
            "before": before,
            "after": after,
        })

    # -- group (Empty) resolution ------------------------------------------
    def _find_group_empty(self, name: str):
        """An existing Empty named ``name`` (the Blender analog of a C4D
        Null group). Prefer a scene Empty of that exact name."""
        try:
            for o in self.doc.scene.objects:
                if self._safe_name(o) == name \
                        and getattr(o, "type", None) == "EMPTY":
                    return o
        except Exception:
            pass
        return None

    def _find_or_create_group(self, name: str):
        empty = self._find_group_empty(name)
        if empty is not None:
            return empty
        bpy = self.bpy
        try:
            empty = bpy.data.objects.new(name, None)  # None data => Empty
        except Exception:
            return None
        master = self._master_collection()
        try:
            if master is not None:
                master.objects.link(empty)
        except Exception:
            pass
        # Fresh empties sit at the world origin already; assert it defensively.
        try:
            empty.location = (0.0, 0.0, 0.0)
        except Exception:
            pass
        return empty

    @staticmethod
    def _is_ancestor_of(obj, other) -> bool:
        """True when ``obj`` is an ancestor of ``other`` (so parenting ``obj``
        under ``other`` would create a cycle)."""
        p = getattr(other, "parent", None)
        while p is not None:
            if p == obj:
                return True
            p = getattr(p, "parent", None)
        return False

    def _reparent_keep_world(self, obj, parent) -> bool:
        """Parent ``obj`` under ``parent`` (or unparent when ``parent`` is
        None) while preserving the world transform. Every bpy access is
        guarded - a huge production scene has objects in odd states."""
        try:
            mw = obj.matrix_world.copy()
        except Exception:
            mw = None
        try:
            obj.parent = parent
        except Exception:
            return False
        if parent is not None:
            try:
                obj.matrix_parent_inverse = parent.matrix_world.inverted()
            except Exception:
                pass
        # Re-assert the captured world matrix (recomputes matrix_basis for the
        # new parent chain) so the object does not visually jump.
        if mw is not None:
            try:
                obj.matrix_world = mw
            except Exception:
                pass
        return True

    # -- collection (layer) linking ----------------------------------------
    def _link_exclusive(self, obj, collection) -> bool:
        """Link ``obj`` into ``collection`` and unlink it from every other
        collection it currently belongs to (layers are exclusive, mirroring a
        C4D layer assignment)."""
        linked = self._ensure_in(collection, obj)
        try:
            for c in list(obj.users_collection):
                if c == collection:
                    continue
                try:
                    c.objects.unlink(obj)
                except Exception:
                    pass
        except Exception:
            pass
        return linked

    @staticmethod
    def _ensure_in(collection, obj) -> bool:
        try:
            collection.objects.link(obj)
            return True
        except Exception:
            # Already linked raises RuntimeError; verify membership.
            try:
                return obj.name in collection.objects
            except Exception:
                return True

    # -- renames -----------------------------------------------------------
    def rename_object(self, guid, new_name: str) -> bool:
        self.last_changes = []
        obj = self._by_guid.get(guid)
        if obj is None:
            return False
        before = self._safe_name(obj)
        if before == new_name:
            return True
        if not self._set_name(obj, new_name):
            return False
        self._log_change(obj, "name", before, self._safe_name(obj))
        self.doc.undo_push("Overseer: rename")
        self.doc.tag_redraw()
        return True

    def apply_renames(self, renames: list[RenameOp]) -> int:
        self.last_changes = []
        renames = list(renames or [])
        if not renames:
            return 0
        count = 0
        for op in renames:
            obj = self._by_guid.get(op.node.guid)
            if obj is None:
                continue
            before = self._safe_name(obj)
            if not self._set_name(obj, op.new_name):
                continue
            # obj.name may carry a Blender-assigned ``.001`` suffix on a global
            # name clash; record the ACTUAL resulting name so revert re-finds it.
            self._log_change(obj, "name", before, self._safe_name(obj))
            count += 1
        if count:
            self.doc.undo_push("Overseer: rename %d" % count)
            self.doc.tag_redraw()
        return count

    # -- reparents ---------------------------------------------------------
    def apply_reparents(self, reparents: list[ReparentOp]) -> int:
        self.last_changes = []
        reparents = list(reparents or [])
        if not reparents:
            return 0
        count = 0
        for op in reparents:
            obj = self._by_guid.get(op.node.guid)
            if obj is None:
                continue
            group = self._find_or_create_group(op.to_group)
            if group is None or group == obj or self._is_ancestor_of(obj, group):
                continue
            if self._reparent_keep_world(obj, group):
                self._log_change(obj, "parent", op.from_group, op.to_group)
                count += 1
        if count:
            self.doc.undo_push("Overseer: reparent %d" % count)
            self.doc.tag_redraw()
        return count

    # -- layers (collections) ----------------------------------------------
    def apply_layers(self, layerops: list[LayerOp]) -> int:
        self.last_changes = []
        layerops = list(layerops or [])
        if not layerops:
            return 0
        count = 0
        for op in layerops:
            obj = self._by_guid.get(op.node.guid)
            if obj is None:
                continue
            before = self._current_layer_name(obj) or ""
            target = self._find_or_create_collection(op.layer)
            if target is None:
                continue
            if self._link_exclusive(obj, target):
                self._log_change(obj, "layer", before, op.layer)
                count += 1
        if count:
            self.doc.undo_push("Overseer: assign collection %d" % count)
            self.doc.tag_redraw()
        return count

    # -- revert ------------------------------------------------------------
    def _resolve_change(self, item: dict):
        obj = self._by_sid.get(item.get("sid"))
        if obj is not None:
            return obj
        wanted = (item.get("after") if item.get("field") == "name"
                  else item.get("name"))
        for cand in self._by_guid.values():
            try:
                if cand.name == wanted:
                    return cand
            except Exception:
                continue
        return None

    def _revert_layer(self, obj, before) -> None:
        if before:
            target = self._find_or_create_collection(before)
            if target is not None:
                self._link_exclusive(obj, target)
                return
        # No previous layer: return the object to the scene master collection.
        master = self._master_collection()
        if master is not None:
            self._link_exclusive(obj, master)

    def _revert_parent(self, obj, before) -> None:
        if before and before not in ("(root)", "/"):
            group = self._find_or_create_group(before)
            if group is not None and group != obj \
                    and not self._is_ancestor_of(obj, group):
                self._reparent_keep_world(obj, group)
                return
        self._reparent_keep_world(obj, None)

    def _revert_texpath(self, item: dict) -> bool:
        """Reverse a texture-path rewrite. The Blender texpaths mixin owns the
        path-writing helpers; call them defensively (they may be absent while
        that mixin is still a stub, in which case the item is reported missing).
        """
        owners_for = getattr(self, "_owners_for_path", None)
        writer = getattr(self, "_write_path_refs", None)
        if owners_for is None or writer is None:
            return False
        before = item.get("before")
        after = item.get("after")
        index = getattr(self, "_owner_index", None)
        idx = None
        try:
            idx = index() if index is not None else None
        except Exception:
            idx = None
        wrote = False
        try:
            for owner in owners_for(after, None, idx):
                if writer(owner, after, before):
                    wrote = True
        except Exception:
            wrote = False
        return wrote

    def revert(self, items) -> dict:
        items = list(items or [])
        reverted = 0
        missing = 0
        results: list = []
        changed = False
        for item in items:
            field = item.get("field")
            note = {"name": item.get("name"), "field": field}

            if field == "texpath":
                if self._revert_texpath(item):
                    changed = True
                    reverted += 1
                    results.append({**note, "status": "reverted"})
                else:
                    missing += 1
                    results.append({**note, "status": "missing"})
                continue

            obj = self._resolve_change(item)
            if obj is None:
                missing += 1
                results.append({**note, "status": "missing"})
                continue
            before = item.get("before")

            if field == "name":
                if self._set_name(obj, before):
                    changed = True
                    reverted += 1
                    results.append({**note, "status": "reverted"})
                else:
                    missing += 1
                    results.append({**note, "status": "missing"})
            elif field == "layer":
                self._revert_layer(obj, before)
                changed = True
                reverted += 1
                results.append({**note, "status": "reverted"})
            elif field == "parent":
                self._revert_parent(obj, before)
                changed = True
                reverted += 1
                results.append({**note, "status": "reverted"})
            else:
                results.append({**note, "status": "skipped"})

        if changed:
            self.doc.undo_push("Overseer: revert")
            self.doc.tag_redraw()
        return {"reverted": reverted, "missing": missing, "results": results}
