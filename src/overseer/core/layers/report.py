from __future__ import annotations

from dataclasses import dataclass, field

from ..scene import model


@dataclass
class LayerInfo:
    name: str
    color: list | None = None
    solo: bool = False
    view: bool = True
    render: bool = True
    locked: bool = False
    object_count: int = 0
    material_count: int = 0
    tag_count: int = 0
    poly_count: int = 0
    all_object_count: int | None = None

    @property
    def empty(self) -> bool:
        objs = (self.object_count if self.all_object_count is None
                else self.all_object_count)
        return objs == 0 and self.material_count == 0 and self.tag_count == 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "solo": self.solo,
            "view": self.view,
            "render": self.render,
            "locked": self.locked,
            "objects": self.object_count,
            "objects_all": (self.object_count if self.all_object_count is None
                            else self.all_object_count),
            "materials": self.material_count,
            "tags": self.tag_count,
            "polys": self.poly_count,
            "empty": self.empty,
        }


def build_layer_report(layer_meta: list, object_counts: dict | None = None,
                       poly_counts: dict | None = None,
                       no_layer: int = 0,
                       all_object_counts: dict | None = None) -> dict:
    object_counts = object_counts or {}
    poly_counts = poly_counts or {}

    def all_count(name: str) -> int | None:
        if all_object_counts is None:
            return None
        return all_object_counts.get(name, 0)

    layers: list[LayerInfo] = []
    seen: set = set()
    for m in layer_meta:
        name = m.get("name", "")
        seen.add(name)
        layers.append(LayerInfo(
            name=name,
            color=m.get("color"),
            solo=bool(m.get("solo", False)),
            view=bool(m.get("view", True)),
            render=bool(m.get("render", True)),
            locked=bool(m.get("locked", False)),
            object_count=object_counts.get(name, 0),
            material_count=int(m.get("materials", 0)),
            tag_count=int(m.get("tags", 0)),
            poly_count=poly_counts.get(name, 0),
            all_object_count=all_count(name)))
    for name, n in object_counts.items():
        if name not in seen:
            seen.add(name)
            layers.append(LayerInfo(
                name=name, object_count=n,
                poly_count=poly_counts.get(name, 0),
                all_object_count=all_count(name)))
    return {
        "layers": [ly.to_dict() for ly in layers],
        "no_layer": no_layer,
        "total_layers": len(layers),
        "empty_layers": sum(1 for ly in layers if ly.empty),
    }


@dataclass
class LayerMismatch:
    node: model.SceneNode = field(compare=False)
    parent_layer: str = ""
    child_layer: str = ""

    @property
    def guid(self) -> int:
        return self.node.guid

    @property
    def name(self) -> str:
        return self.node.name

    def to_dict(self) -> dict:
        return {
            "guid": self.guid,
            "name": self.name,
            "path": self.node.path,
            "parent": self.node.parent.name if self.node.parent else "",
            "parent_layer": self.parent_layer,
            "child_layer": self.child_layer,
        }


def find_layer_mismatches(tree: model.SceneTree,
                          keep: set | None = None) -> list[LayerMismatch]:
    keep = keep or set()
    out: list[LayerMismatch] = []
    for n in tree.walk():
        if n.parent is None:
            continue
        parent_layer = n.parent.layer
        child_layer = n.layer
        if not parent_layer or not child_layer:
            continue
        if parent_layer == child_layer:
            continue
        if n.name in keep:
            continue
        out.append(LayerMismatch(node=n, parent_layer=parent_layer,
                                 child_layer=child_layer))
    return out

