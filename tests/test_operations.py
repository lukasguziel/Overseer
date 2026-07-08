from sceneorg.core import model
from sceneorg.core.ops import LayerOp, Operation, RenameOp, ReparentOp, Writer


class RecordingWriter(Writer):
    def __init__(self):
        self.calls = []

    def rename(self, node, new_name):
        self.calls.append(("rename", node.name, new_name))

    def reparent(self, node, to_group):
        self.calls.append(("reparent", node.name, to_group))

    def assign_layer(self, node, layer):
        self.calls.append(("layer", node.name, layer))


def _node(name="Cube", guid=7):
    return model.SceneNode(name=name, guid=guid)


def test_ops_link_back_to_node():
    # setup
    n = _node("Wuerfel", guid=3)

    # do it
    op = RenameOp(node=n, new_name="Cube")

    # postcondition
    assert op.guid == 3
    assert op.name == "Wuerfel"
    assert op.old_name == "Wuerfel"
    assert op.node is n


def test_ops_apply_polymorphically_through_writer():
    # setup
    n = _node("Cube", guid=1)
    ops: list[Operation] = [
        RenameOp(node=n, new_name="Box"),
        ReparentOp(node=n, to_group="Furniture", from_group="(root)"),
        LayerOp(node=n, layer="Proxies"),
    ]
    w = RecordingWriter()

    # do it
    for op in ops:
        op.apply(w)

    # postcondition
    assert w.calls == [
        ("rename", "Cube", "Box"),
        ("reparent", "Cube", "Furniture"),
        ("layer", "Cube", "Proxies"),
    ]


def test_op_to_dict_uses_live_node():
    # setup
    n = _node("Lamp", guid=9)

    # postcondition
    assert RenameOp(node=n, new_name="KeyLight").to_dict() == {
        "guid": 9, "old": "Lamp", "new": "KeyLight", "rules": ["casing"]}
    assert LayerOp(node=n, layer="Lights").to_dict() == {
        "guid": 9, "name": "Lamp", "layer": "Lights"}
