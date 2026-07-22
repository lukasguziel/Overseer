"""ApplyOps - rename / reparent / assign-collection / revert for Blender.

The Blender twin of ``cinema/organize/apply.py``. Blender's undo model groups by
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

Blender's ``bpy.data.objects`` / ``bpy.data.collections`` are ONE file-global
namespace per id-type: creating or renaming to an already-taken name never
raises, Blender silently appends ``.001``. So every mutation reads back the
ACTUAL name after writing it, group Empties are keyed by a durable
``overseer_group`` id-property (not by their fragile ``.name``), rename plans
are applied in two phases (park to temp names, then assign disambiguated final
names) so cross-parent duplicates and A<->B swaps cannot silently collide, and
collection exclusivity is scoped to the ACTIVE scene's own collection tree so a
layer assignment never strips membership from another scene's / an orphan /
a rigid-body-world collection.
"""
from __future__ import annotations

from ...core.organize.journal import change_item
from ...core.organize.ops import LayerOp, RenameOp, ReparentOp
from ..scene.readers import stable_id

GROUP_IDPROP = "overseer_group"


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
        self.last_changes.append(change_item(
            stable_id(obj), self._safe_name(obj), field, before, after))

    # -- group (Empty) resolution ------------------------------------------
    @staticmethod
    def _group_key(name) -> str:
        return (name or "").strip().lower()

    def _group_index(self) -> dict:
        """Case-insensitive index of the active scene's group Empties, built
        ONCE per batch. Empties stamped with the ``overseer_group`` id-property
        win over a plain name match (their identity survives a ``.001`` rename
        collision), mirroring the C4D twin's case-insensitive lookup."""
        by_name: dict = {}
        by_id: dict = {}
        try:
            objs = list(self.doc.scene.objects)
        except Exception:
            objs = []
        for o in objs:
            try:
                if getattr(o, "type", None) != "EMPTY":
                    continue
            except Exception:
                continue
            try:
                gid = o.get(GROUP_IDPROP)
            except Exception:
                gid = None
            if gid:
                by_id.setdefault(self._group_key(str(gid)), o)
            by_name.setdefault(self._group_key(self._safe_name(o)), o)
        by_name.update(by_id)
        return by_name

    def _create_group(self, name: str):
        """Create (or reuse an orphan/existing) group Empty named ``name`` and
        stamp its durable ``overseer_group`` id-property. Reads back the real
        ``.name`` (Blender may append ``.001`` if the name is globally taken by
        another object)."""
        bpy = self.bpy
        empty = None
        try:
            existing = bpy.data.objects.get(name)
        except Exception:
            existing = None
        if existing is not None and getattr(existing, "type", None) == "EMPTY":
            empty = existing
        if empty is None:
            try:
                empty = bpy.data.objects.new(name, None)  # None data => Empty
            except Exception:
                return None
        try:
            empty[GROUP_IDPROP] = name
        except Exception:
            pass
        master = self._master_collection()
        try:
            if master is not None and self._safe_name(empty) not in master.objects:
                master.objects.link(empty)
        except Exception:
            pass
        try:
            empty.location = (0.0, 0.0, 0.0)
        except Exception:
            pass
        return empty

    def _find_or_create_group(self, name: str, index: dict, created: dict):
        """Resolve the group Empty for ``name``, reusing the one already found
        or made earlier in THIS batch so N reparents to one group share ONE
        Empty instead of spawning an orphan per op."""
        key = self._group_key(name)
        hit = created.get(key)
        if hit is not None:
            return hit
        hit = index.get(key)
        if hit is None:
            hit = self._create_group(name)
        if hit is not None:
            created[key] = hit
            index[key] = hit
            index[self._group_key(self._safe_name(hit))] = hit
        return hit

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
        if mw is not None:
            try:
                obj.matrix_world = mw
            except Exception:
                pass
        return True

    # -- collection (layer) linking ----------------------------------------
    def _scene_collection_set(self) -> set:
        """The set of collections that belong to the ACTIVE scene (its master
        collection + every collection reachable from it). Used to scope
        exclusive layer assignment so it never touches collections owned by
        another scene, an orphan/asset container, or the rigid-body world."""
        cols: set = set()
        master = self._master_collection()
        if master is not None:
            cols.add(master)
        try:
            for c in self._scene_collections():
                cols.add(c)
        except Exception:
            pass
        return cols

    def _resolve_collection(self, name: str, cache: dict):
        """Find-or-create the collection for ``name``, memoised per batch so a
        repeated target layer resolves once (the C4D twin threads the same
        cache)."""
        key = name or ""
        if key in cache:
            return cache[key]
        col = self._find_or_create_collection(name)
        cache[key] = col
        return col

    def _link_exclusive(self, obj, collection, scene_cols=None) -> bool:
        """Link ``obj`` into ``collection`` and unlink it from every OTHER
        collection of the active scene it currently belongs to (layers are
        exclusive within the scene, mirroring a C4D layer assignment). Never
        unlinks from collections outside the scene: ``obj.users_collection`` is
        a file-global reverse-lookup, so we intersect it with the scene's own
        collection set."""
        linked = self._ensure_in(collection, obj)
        if scene_cols is None:
            scene_cols = self._scene_collection_set()
        try:
            for c in list(obj.users_collection):
                if c == collection or c not in scene_cols:
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
        except RuntimeError:
            # Already-linked raises RuntimeError; verify membership.
            try:
                return obj.name in collection.objects
            except Exception:
                return False
        except Exception:
            return False

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

    def _external_object_names(self, temp_names: set) -> set:
        """Every object name currently taken in the file EXCEPT the batch
        objects (which are parked under temp names). Seeds the disambiguation
        so a final name never collides with an untouched object."""
        names: set = set()
        try:
            objs = list(self.bpy.data.objects)
        except Exception:
            objs = []
        for o in objs:
            nm = self._safe_name(o)
            if nm and nm not in temp_names:
                names.add(nm)
        return names

    @staticmethod
    def _unique_object_name(wanted: str, taken: set) -> str:
        if wanted not in taken:
            return wanted
        i = 1
        while True:
            cand = "%s.%03d" % (wanted, i)
            if cand not in taken:
                return cand
            i += 1

    def apply_renames(self, renames: list[RenameOp]) -> int:
        self.last_changes = []
        renames = list(renames or [])
        if not renames:
            return 0

        pairs: list = []
        for op in renames:
            try:
                obj = self._by_guid.get(op.node.guid)
                if obj is None:
                    continue
                pairs.append((obj, op.new_name, self._safe_name(obj)))
            except Exception:
                continue
        if not pairs:
            return 0

        # Phase 1: park every targeted object under a guaranteed-unique temp
        # name so no final assignment collides with an object still holding an
        # old name (handles A<->B swaps/cycles and cross-parent duplicates that
        # Blender's file-global object namespace would otherwise ".001"-suffix).
        temp_names: set = set()
        for i, (obj, _final, _before) in enumerate(pairs):
            if self._set_name(obj, "__ovr_tmp_%d__" % i):
                temp_names.add(self._safe_name(obj))

        # Phase 2: assign final names, disambiguating against names taken by
        # objects OUTSIDE the batch plus names already assigned within it.
        taken = self._external_object_names(temp_names)
        count = 0
        for obj, final, before in pairs:
            try:
                self._set_name(obj, self._unique_object_name(final, taken))
                actual = self._safe_name(obj)
                taken.add(actual)
                self._log_change(obj, "name", before, actual)
                count += 1
            except Exception:
                continue
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
        index = self._group_index()
        created: dict = {}
        count = 0
        for op in reparents:
            try:
                obj = self._by_guid.get(op.node.guid)
                if obj is None:
                    continue
                group = self._find_or_create_group(op.to_group, index, created)
                if group is None or group == obj \
                        or self._is_ancestor_of(obj, group):
                    continue
                if self._reparent_keep_world(obj, group):
                    self._log_change(obj, "parent", op.from_group, op.to_group)
                    count += 1
            except Exception:
                continue
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
        scene_cols = self._scene_collection_set()
        col_cache: dict = {}
        count = 0
        for op in layerops:
            try:
                obj = self._by_guid.get(op.node.guid)
                if obj is None:
                    continue
                before = self._current_layer_name(obj) or ""
                target = self._resolve_collection(op.layer, col_cache)
                if target is None:
                    continue
                scene_cols.add(target)
                if self._link_exclusive(obj, target, scene_cols):
                    # target.name may carry a ".001" suffix on a global
                    # collection name clash; log the ACTUAL collection so
                    # revert re-finds it.
                    self._log_change(obj, "layer", before,
                                     self._safe_name(target))
                    count += 1
            except Exception:
                continue
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

    def _revert_layer(self, obj, before, scene_cols, col_cache) -> None:
        if before:
            target = self._resolve_collection(before, col_cache)
            if target is not None:
                scene_cols.add(target)
                self._link_exclusive(obj, target, scene_cols)
                return
        # No previous layer: return the object to the scene master collection.
        master = self._master_collection()
        if master is not None:
            self._link_exclusive(obj, master, scene_cols)

    def _revert_parent(self, obj, before, index, created) -> None:
        if before and before not in ("(root)", "/"):
            group = self._find_or_create_group(before, index, created)
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

        scene_cols = self._scene_collection_set()
        col_cache: dict = {}
        group_index = self._group_index()
        group_created: dict = {}

        for item in items:
            try:
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
                    # obj.name = before silently ".001"-suffixes when another
                    # object already holds ``before``; report "reverted" only
                    # when the name actually became ``before``, leaving the
                    # journal entry revertible otherwise.
                    if self._set_name(obj, before) \
                            and self._safe_name(obj) == before:
                        changed = True
                        reverted += 1
                        results.append({**note, "status": "reverted"})
                    else:
                        missing += 1
                        results.append({**note, "status": "collision"})
                elif field == "layer":
                    self._revert_layer(obj, before, scene_cols, col_cache)
                    changed = True
                    reverted += 1
                    results.append({**note, "status": "reverted"})
                elif field == "parent":
                    self._revert_parent(obj, before, group_index,
                                        group_created)
                    changed = True
                    reverted += 1
                    results.append({**note, "status": "reverted"})
                else:
                    results.append({**note, "status": "skipped"})
            except Exception:
                missing += 1
                results.append({"name": item.get("name"),
                                "field": item.get("field"),
                                "status": "missing"})

        if changed:
            self.doc.undo_push("Overseer: revert")
            self.doc.tag_redraw()
        return {"reverted": reverted, "missing": missing, "results": results}
