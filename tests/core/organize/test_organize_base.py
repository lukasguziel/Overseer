"""The OrganizeBase template-method surface, exercised through a tiny
in-memory host. Proves the shared rename workflow calls the host primitives,
brackets the edit through the undo hooks, and emits the canonical journal row
shape - without importing any host (cinema/blender) module."""
from overseer.core.organize.base import OrganizeBase
from overseer.core.organize.ops import RenameOp
from overseer.core.scene import model


class _Obj:
    def __init__(self, sid, name):
        self.sid = sid
        self.name = name


class _FakeOrganize(OrganizeBase):
    """A host that keeps objects in a dict keyed by guid and records every
    undo-hook call so a test can assert the bracket order."""

    def __init__(self, objs):
        self._objs = {o.sid: o for o in objs}
        self.last_changes = []
        self.edits = []
        self.notified = 0
        self.allow_set = True

    def resolve_object(self, guid):
        return self._objs.get(guid)

    def get_object_name(self, obj):
        return obj.name

    def set_object_name(self, obj, name):
        if not self.allow_set:
            return False
        obj.name = name
        return True

    def object_sid(self, obj):
        return obj.sid

    def begin_edit(self):
        self.edits.append("begin")

    def touch(self, obj, kind):
        self.edits.append(("touch", obj.sid, kind))

    def end_edit(self, label):
        self.edits.append(("end", label))

    def notify(self):
        self.notified += 1

    def apply_reparents(self, reparents):
        return 0

    def apply_layers(self, layerops):
        return 0

    def revert(self, items):
        return {"reverted": 0, "missing": 0, "results": []}


def _rename(guid, old, new):
    return RenameOp(node=model.SceneNode(old, guid=guid), new_name=new)


def test_apply_renames_runs_the_shared_template():
    # setup
    a, b = _Obj(11, "cube"), _Obj(22, "lampe")
    host = _FakeOrganize([a, b])

    # do it
    applied = host.apply_renames([_rename(11, "cube", "Cube"),
                                  _rename(22, "lampe", "Lamp")])

    # postcondition: primitives mutated, canonical rows logged, one bracket
    assert applied == 2
    assert (a.name, b.name) == ("Cube", "Lamp")
    assert host.last_changes == [
        {"sid": 11, "name": "Cube", "field": "name",
         "before": "cube", "after": "Cube"},
        {"sid": 22, "name": "Lamp", "field": "name",
         "before": "lampe", "after": "Lamp"}]
    assert host.edits[0] == "begin"
    assert host.edits[-1] == ("end", "Overseer: rename 2")
    assert host.notified == 1


def test_apply_renames_skips_missing_guid():
    # setup
    a = _Obj(11, "cube")
    host = _FakeOrganize([a])

    # do it
    applied = host.apply_renames([_rename(99, "gone", "Ghost"),
                                  _rename(11, "cube", "Cube")])

    # postcondition: the absent object is skipped, the real one still renamed
    assert applied == 1
    assert [c["sid"] for c in host.last_changes] == [11]
    assert ("touch", 99, "name") not in host.edits


def test_apply_renames_empty_opens_no_undo_bracket():
    # setup
    host = _FakeOrganize([])

    # do it
    applied = host.apply_renames([])

    # postcondition
    assert applied == 0
    assert host.edits == []
    assert host.notified == 0


def test_rename_object_logs_change_and_brackets_the_edit():
    # setup
    a = _Obj(11, "cube")
    host = _FakeOrganize([a])

    # do it
    ok = host.rename_object(11, "Cube")

    # postcondition
    assert ok is True
    assert a.name == "Cube"
    assert host.last_changes == [
        {"sid": 11, "name": "Cube", "field": "name",
         "before": "cube", "after": "Cube"}]
    assert host.edits == ["begin", ("touch", 11, "name"),
                          ("end", "Overseer: rename")]
    assert host.notified == 1


def test_rename_object_noop_when_name_unchanged():
    # setup
    a = _Obj(11, "Cube")
    host = _FakeOrganize([a])

    # do it
    ok = host.rename_object(11, "Cube")

    # postcondition: no edit, no journal row, no undo bracket
    assert ok is True
    assert host.last_changes == []
    assert host.edits == []


def test_rename_object_missing_guid_returns_false():
    # setup
    host = _FakeOrganize([])

    # do it
    ok = host.rename_object(1, "X")

    # postcondition
    assert ok is False
    assert host.edits == []


def test_rename_object_aborts_when_set_primitive_fails():
    # setup: a host whose write primitive refuses (mirrors a Blender name clash)
    a = _Obj(11, "cube")
    host = _FakeOrganize([a])
    host.allow_set = False

    # do it
    ok = host.rename_object(11, "Cube")

    # postcondition: the template stops, nothing is logged
    assert ok is False
    assert host.last_changes == []
    assert a.name == "cube"
