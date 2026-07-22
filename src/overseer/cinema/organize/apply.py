from __future__ import annotations

import c4d

from ...core.organize.base import OrganizeBase
from ...core.organize.ops import LayerOp, ReparentOp
from ..scene.readers import stable_id


class CinemaOrganize(OrganizeBase):

    # -- OrganizeBase primitives -------------------------------------------
    def resolve_object(self, guid):
        return self._by_guid.get(guid)

    def get_object_name(self, obj) -> str:
        return obj.GetName()

    def set_object_name(self, obj, name: str) -> bool:
        obj.SetName(name)
        return True

    def object_sid(self, obj) -> int:
        return stable_id(obj)

    def begin_edit(self) -> None:
        self.doc.StartUndo()

    def touch(self, obj, kind: str) -> None:
        self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)

    def end_edit(self, label: str) -> None:
        self.doc.EndUndo()

    def notify(self) -> None:
        c4d.EventAdd()

    # -- group resolution --------------------------------------------------
    def _match_group(self, obj, segment: str) -> bool:
        if not obj.CheckType(c4d.Onull):
            return False
        name = obj.GetName()
        return name.lower() == segment.lower()

    def _resolve_group_path(self, path: str):
        parent = None
        for segment in path.split("/"):
            found = None
            child = parent.GetDown() if parent is not None \
                else self.doc.GetFirstObject()
            while child:
                if self._match_group(child, segment):
                    found = child
                    break
                child = child.GetNext()
            if found is None:
                return None
            parent = found
        return parent

    def _find_group_anywhere(self, segment: str):
        stack = [self.doc.GetFirstObject()]
        while stack:
            op = stack.pop()
            while op:
                if self._match_group(op, segment):
                    return op
                down = op.GetDown()
                if down:
                    stack.append(down)
                op = op.GetNext()
        return None

    def ensure_group_path(self, path: str, created: list[object]) -> object:
        parent = None
        for segment in path.split("/"):
            found = None
            child = parent.GetDown() if parent is not None \
                else self.doc.GetFirstObject()
            while child:
                if self._match_group(child, segment):
                    found = child
                    break
                child = child.GetNext()
            if found is None:
                found = c4d.BaseObject(c4d.Onull)
                found.SetName(segment)
                if parent is not None:
                    found.InsertUnderLast(parent)
                else:
                    self.doc.InsertObject(found)
                self.doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, found)
                created.append(found)
            parent = found
        return parent

    # -- layers ------------------------------------------------------------
    def _do_layers(self, layerops: list[LayerOp], created: list,
                   cache: dict) -> int:
        count = 0
        for op in layerops:
            obj = self.resolve_object(op.guid)
            if obj is None:
                continue
            before = self._current_layer_name(obj)
            layer = self._find_or_create_layer(op.layer, created, cache)
            self.touch(obj, "layer")
            obj.SetLayerObject(layer)
            self._log_change(obj, "layer", before, op.layer)
            count += 1
        return count

    def apply_layers(self, layerops: list[LayerOp]) -> int:
        self.last_changes = []
        if not layerops:
            return 0
        self.begin_edit()
        created: list = []
        cache: dict = {}
        count = self._do_layers(layerops, created, cache)
        self.end_edit("Overseer: assign layer %d" % count)
        self.notify()
        return count

    # -- reparents ---------------------------------------------------------
    @staticmethod
    def _is_ancestor_of(obj, group) -> bool:
        up = group.GetUp()
        while up is not None:
            if up == obj:
                return True
            up = up.GetUp()
        return False

    def _do_reparents(self, reparents: list[ReparentOp], created: list) -> int:
        count = 0
        for op in reparents:
            obj = self.resolve_object(op.guid)
            if obj is None:
                continue
            group = self.ensure_group_path(op.to_group, created)
            if obj == group or self._is_ancestor_of(obj, group):
                continue
            self.touch(obj, "parent")
            mg = obj.GetMg()
            obj.Remove()
            obj.InsertUnderLast(group)
            obj.SetMg(mg)
            self._log_change(obj, "parent", op.from_group, op.to_group)
            count += 1
        return count

    def apply_reparents(self, reparents: list[ReparentOp]) -> int:
        self.last_changes = []
        if not reparents:
            return 0
        self.begin_edit()
        created: list[object] = []
        count = self._do_reparents(reparents, created)
        self.end_edit("Overseer: reparent %d" % count)
        self.notify()
        return count

    # -- revert ------------------------------------------------------------
    def _resolve_change(self, item: dict):
        obj = self._by_sid.get(item.get("sid"))
        if obj is not None:
            return obj
        wanted = item.get("after") if item.get("field") == "name" else item.get("name")
        for cand in self._by_guid.values():
            if cand.GetName() == wanted:
                return cand
        return None

    def revert(self, items: list[dict]) -> dict:
        reverted = 0
        missing = 0
        results: list = []
        self.begin_edit()
        created: list = []
        cache: dict = {}
        index: dict | None = None
        for item in items:
            field = item.get("field")
            note = {"name": item.get("name"), "field": field}

            if field == "texpath":
                before = item.get("before")
                after = item.get("after")
                if index is None:
                    index = self._owner_index()
                wrote = False
                for owner in self._owners_for_path(after, None, index):
                    if self._write_path_refs(owner, after, before):
                        wrote = True
                if wrote:
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
                self.touch(obj, "name")
                obj.SetName(before)
            elif field == "layer":
                self.touch(obj, "layer")
                if before:
                    obj.SetLayerObject(
                        self._find_or_create_layer(before, created, cache))
                else:
                    obj.SetLayerObject(None)
            elif field == "parent":
                self.touch(obj, "parent")
                mg = obj.GetMg()
                obj.Remove()
                if before and before not in ("(root)", "/"):
                    group = self._resolve_group_path(before) \
                        or self._find_group_anywhere(before.split("/")[-1]) \
                        or self.ensure_group_path(before, created)
                    obj.InsertUnderLast(group)
                else:
                    self.doc.InsertObject(obj)
                obj.SetMg(mg)
            else:
                results.append({**note, "status": "skipped"})
                continue
            reverted += 1
            results.append({**note, "status": "reverted"})

        self.end_edit("Overseer: revert")
        self.notify()
        return {"reverted": reverted, "missing": missing, "results": results}
