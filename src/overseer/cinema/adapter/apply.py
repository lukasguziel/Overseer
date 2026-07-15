from __future__ import annotations

import collections

import c4d

from ...core.ops import LayerOp, RenameOp, ReparentOp
from .readers import stable_id


class ApplyOps:

    def _match_group(self, obj, segment: str, canonical=None) -> bool:
        if not obj.CheckType(c4d.Onull):
            return False
        name = obj.GetName()
        if name.lower() == segment.lower():
            return True
        return canonical is not None and canonical(name) == segment

    def _resolve_group_path(self, path: str, canonical=None):
        parent = None
        for segment in path.split("/"):
            found = None
            child = parent.GetDown() if parent is not None \
                else self.doc.GetFirstObject()
            while child:
                if self._match_group(child, segment, canonical):
                    found = child
                    break
                child = child.GetNext()
            if found is None:
                return None
            parent = found
        return parent

    def _find_group_anywhere(self, segment: str, canonical=None):
        stack = [self.doc.GetFirstObject()]
        while stack:
            op = stack.pop()
            while op:
                if self._match_group(op, segment, canonical):
                    return op
                down = op.GetDown()
                if down:
                    stack.append(down)
                op = op.GetNext()
        return None

    def ensure_group_path(self, path: str, created: list[object],
                          canonical=None) -> object:
        parent = None
        for segment in path.split("/"):
            found = None
            child = parent.GetDown() if parent is not None \
                else self.doc.GetFirstObject()
            while child:
                if self._match_group(child, segment, canonical):
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

    def _log_change(self, obj, field: str, before, after) -> None:
        self.last_changes.append({
            "sid": stable_id(obj),
            "name": obj.GetName(),
            "field": field,
            "before": before,
            "after": after,
        })

    def _do_renames(self, renames: list[RenameOp]) -> int:
        count = 0
        for op in renames:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            before = obj.GetName()
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetName(op.new_name)
            self._log_change(obj, "name", before, op.new_name)
            count += 1
        return count

    def apply_renames(self, renames: list[RenameOp]) -> int:
        self.last_changes = []
        if not renames:
            return 0
        self.doc.StartUndo()
        count = self._do_renames(renames)
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    def rename_object(self, guid: int, new_name: str) -> bool:
        obj = self._by_guid.get(guid)
        if obj is None:
            return False
        self.last_changes = []
        before = obj.GetName()
        if before == new_name:
            return True
        self.doc.StartUndo()
        self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
        obj.SetName(new_name)
        self._log_change(obj, "name", before, new_name)
        self.doc.EndUndo()
        c4d.EventAdd()
        return True

    def _do_layers(self, layerops: list[LayerOp], created: list,
                   cache: dict) -> int:
        count = 0
        for op in layerops:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            before = self._current_layer_name(obj)
            layer = self._find_or_create_layer(op.layer, created, cache)
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            obj.SetLayerObject(layer)
            self._log_change(obj, "layer", before, op.layer)
            count += 1
        return count

    def apply_layers(self, layerops: list[LayerOp]) -> int:
        self.last_changes = []
        if not layerops:
            return 0
        self.doc.StartUndo()
        created: list = []
        cache: dict = {}
        count = self._do_layers(layerops, created, cache)
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    @staticmethod
    def _is_ancestor_of(obj, group) -> bool:
        up = group.GetUp()
        while up is not None:
            if up == obj:
                return True
            up = up.GetUp()
        return False

    def _do_reparents(self, reparents: list[ReparentOp], created: list,
                      canonical=None) -> int:
        count = 0
        for op in reparents:
            obj = self._by_guid.get(op.guid)
            if obj is None:
                continue
            group = self.ensure_group_path(op.to_group, created, canonical)
            if obj == group or self._is_ancestor_of(obj, group):
                continue
            self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
            mg = obj.GetMg()
            obj.Remove()
            obj.InsertUnderLast(group)
            obj.SetMg(mg)
            self._log_change(obj, "parent", op.from_group, op.to_group)
            count += 1
        return count

    def apply_reparents(self, reparents: list[ReparentOp], canonical=None) -> int:
        self.last_changes = []
        if not reparents:
            return 0
        self.doc.StartUndo()
        created: list[object] = []
        count = self._do_reparents(reparents, created, canonical)
        self.doc.EndUndo()
        c4d.EventAdd()
        return count

    def apply_bundle(self, renames: list[RenameOp],
                     reparents: list[ReparentOp],
                     layerops: list[LayerOp],
                     canonical=None) -> dict:
        self.last_changes = []
        if not (renames or reparents or layerops):
            return {"renames": 0, "reparents": 0, "layers": 0}
        self.doc.StartUndo()
        created: list = []
        lay_cache: dict = {}
        renamed = self._do_renames(renames)
        reparented = self._do_reparents(reparents, created, canonical)
        layered = self._do_layers(layerops, created, lay_cache)
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"renames": renamed, "reparents": reparented, "layers": layered}

    def _resolve_change(self, item: dict):
        obj = self._by_sid.get(item.get("sid"))
        if obj is not None:
            return obj
        wanted = item.get("after") if item.get("field") == "name" else item.get("name")
        for cand in self._by_guid.values():
            if cand.GetName() == wanted:
                return cand
        return None

    def revert(self, items: list[dict], canonical=None) -> dict:
        reverted = 0
        missing = 0
        results: list = []
        self.doc.StartUndo()
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
                self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                obj.SetName(before)
            elif field == "layer":
                self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                if before:
                    obj.SetLayerObject(
                        self._find_or_create_layer(before, created, cache))
                else:
                    obj.SetLayerObject(None)
            elif field == "parent":
                self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                mg = obj.GetMg()
                obj.Remove()
                if before and before not in ("(root)", "/"):
                    group = self._resolve_group_path(before, canonical) \
                        or self._find_group_anywhere(before.split("/")[-1],
                                                     canonical) \
                        or self.ensure_group_path(before, created, canonical)
                    obj.InsertUnderLast(group)
                else:
                    self.doc.InsertObject(obj)
                obj.SetMg(mg)
            else:
                results.append({**note, "status": "skipped"})
                continue
            reverted += 1
            results.append({**note, "status": "reverted"})

        self.doc.EndUndo()
        c4d.EventAdd()
        return {"reverted": reverted, "missing": missing, "results": results}

    def apply_plan(self, operations: list[dict]) -> dict:
        refs: dict = {}
        created: list = []
        lay_cache: dict = {}
        applied: collections.Counter = collections.Counter()
        errors: list = []

        def resolve(ref):
            if ref is None:
                return None
            if isinstance(ref, str) and ref.startswith("$"):
                return refs.get(ref)
            return self._by_guid.get(ref)

        self.doc.StartUndo()
        for i, opd in enumerate(operations):
            kind = opd.get("op")
            try:
                if kind == "group":
                    null = c4d.BaseObject(c4d.Onull)
                    null.SetName(opd.get("name", "GROUP"))
                    parent = resolve(opd.get("under"))
                    if parent is not None:
                        null.InsertUnderLast(parent)
                    else:
                        self.doc.InsertObject(null)
                    self.doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, null)
                    created.append(null)
                    if opd.get("id"):
                        refs[opd["id"]] = null
                    applied["group"] += 1
                elif kind == "rename":
                    obj = resolve(opd.get("target"))
                    if obj is None:
                        errors.append("rename #%d: target missing" % i)
                        continue
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    obj.SetName(opd.get("to", obj.GetName()))
                    applied["rename"] += 1
                elif kind == "move":
                    obj = resolve(opd.get("target"))
                    dest = resolve(opd.get("into"))
                    if obj is None:
                        errors.append("move #%d: target missing" % i)
                        continue
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    mg = obj.GetMg()
                    obj.Remove()
                    if dest is not None:
                        obj.InsertUnderLast(dest)
                    else:
                        self.doc.InsertObject(obj)
                    obj.SetMg(mg)
                    applied["move"] += 1
                elif kind == "layer":
                    obj = resolve(opd.get("target"))
                    if obj is None:
                        errors.append("layer #%d: target missing" % i)
                        continue
                    layer = self._find_or_create_layer(
                        opd.get("layer", "Layer"), created, lay_cache)
                    self.doc.AddUndo(c4d.UNDOTYPE_CHANGE, obj)
                    obj.SetLayerObject(layer)
                    applied["layer"] += 1
                else:
                    errors.append("op #%d: unknown '%s'" % (i, kind))
            except Exception as ex:  # noqa: BLE001
                errors.append("op #%d (%s): %s" % (i, kind, ex))
        self.doc.EndUndo()
        c4d.EventAdd()
        return {"applied": dict(applied), "errors": errors,
                "total": sum(applied.values())}
