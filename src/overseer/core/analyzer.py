from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..naming import casing as naming
from ..naming import translate as translatemod
from ..structure.standard import StructureStandard, default_standard
from . import model


@dataclass
class SceneReport:
    file: str = ""
    object_count: int = 0
    max_depth: int = 0
    total_points: int = 0
    total_polys: int = 0
    types: dict[str, int] = field(default_factory=dict)
    categories: dict[str, int] = field(default_factory=dict)
    casing: dict[str, int] = field(default_factory=dict)
    language: dict[str, int] = field(default_factory=dict)
    top_level: list[dict] = field(default_factory=list)
    polys_by_category: dict[str, int] = field(default_factory=dict)
    polys_by_group: dict[str, int] = field(default_factory=dict)
    largest: list[dict] = field(default_factory=list)
    lights_by_group: dict[str, int] = field(default_factory=dict)
    cameras_by_group: dict[str, int] = field(default_factory=dict)
    structure_compliance: float = 1.0
    misplaced: list[dict] = field(default_factory=list)
    nodes: list[dict] = field(default_factory=list)
    hidden_count: int = 0
    layers_by_name: dict[str, int] = field(default_factory=dict)
    polys_by_layer: dict[str, int] = field(default_factory=dict)
    no_layer_count: int = 0

    def to_dict(self) -> dict:
        return {
            "file": self.file,
            "object_count": self.object_count,
            "max_depth": self.max_depth,
            "total_points": self.total_points,
            "total_polys": self.total_polys,
            "types": self.types,
            "categories": self.categories,
            "casing": self.casing,
            "language": self.language,
            "top_level": self.top_level,
            "polys_by_category": self.polys_by_category,
            "polys_by_group": self.polys_by_group,
            "largest": self.largest,
            "lights_by_group": self.lights_by_group,
            "cameras_by_group": self.cameras_by_group,
            "structure_compliance": round(self.structure_compliance, 3),
            "misplaced": self.misplaced,
            "nodes": self.nodes,
            "hidden_count": self.hidden_count,
            "layers_by_name": self.layers_by_name,
            "polys_by_layer": self.polys_by_layer,
            "no_layer_count": self.no_layer_count,
        }


class SceneAnalyzer:
    def __init__(self, standard: StructureStandard = None) -> None:
        self.standard = standard or default_standard()

    def analyze(self, tree: model.SceneTree, file_name: str = "",
                scope: set | None = None,
                include_hidden: bool = True) -> SceneReport:
        report = SceneReport(file=file_name)

        types: Counter = Counter()
        categories: Counter = Counter()
        casing: Counter = Counter()
        language: Counter = Counter()
        light_groups: Counter = Counter()
        camera_groups: Counter = Counter()
        polys_by_cat: Counter = Counter()
        polys_by_group: Counter = Counter()
        layer_counts: Counter = Counter()
        layer_polys: Counter = Counter()
        no_layer_count = 0
        node_dicts: list[dict] = []
        assets: list[tuple] = []
        total_points = 0
        total_polys = 0
        max_depth = 0
        count = 0

        top_nodes: list = []
        active_guids: set = set()
        hidden_count = 0
        filtering = scope is not None or not include_hidden

        def _active(node) -> bool:
            if scope is not None and node.guid not in scope:
                return False
            return include_hidden or node.visible

        for n in tree.walk():
            if not n.visible:
                hidden_count += 1
            if not _active(n):
                continue
            active_guids.add(n.guid)
            if filtering and (n.parent is None or n.parent.guid not in active_guids):
                top_nodes.append(n)
            count += 1
            if n.depth > max_depth:
                max_depth = n.depth
            cas = naming.detect_casing(n.name).value
            lang = translatemod.detect_name_language(n.name)

            types[n.type_name] += 1
            categories[n.category] += 1
            casing[cas] += 1
            language[lang] += 1

            total_points += n.point_count
            total_polys += n.poly_count
            if n.poly_count:
                polys_by_cat[n.category] += n.poly_count
                polys_by_group[n.top_group().name] += n.poly_count
                assets.append((n.poly_count, n.guid, n.name, n.type_name, n.point_count))

            if n.category == model.CAT_LIGHT:
                light_groups[n.top_group().name] += 1
            elif n.category == model.CAT_CAMERA:
                camera_groups[n.top_group().name] += 1

            if n.layer:
                layer_counts[n.layer] += 1
                layer_polys[n.layer] += n.poly_count
            else:
                no_layer_count += 1

            node_dicts.append({
                "guid": n.guid,
                "name": n.name, "type": n.type_name, "category": n.category,
                "depth": n.depth, "path": n.path, "casing": cas,
                "language": lang, "children": n.child_count,
                "points": n.point_count, "polygons": n.poly_count,
                "visible": n.visible, "layer": n.layer,
            })

        report.object_count = count
        report.hidden_count = hidden_count
        report.max_depth = max_depth
        report.total_points = total_points
        report.total_polys = total_polys
        report.types = dict(types)
        report.categories = dict(categories)
        report.casing = dict(casing)
        report.language = dict(language)
        report.polys_by_category = dict(polys_by_cat)
        report.polys_by_group = dict(polys_by_group.most_common(12))
        assets.sort(key=lambda a: a[0], reverse=True)
        report.largest = [
            {"guid": gd, "name": nm, "type": tp, "polygons": pl, "points": pt}
            for pl, gd, nm, tp, pt in assets[:12]
        ]
        report.lights_by_group = dict(light_groups)
        report.cameras_by_group = dict(camera_groups)
        report.layers_by_name = dict(layer_counts)
        report.polys_by_layer = dict(layer_polys)
        report.no_layer_count = no_layer_count
        report.top_level = [
            {"name": r.name, "type": r.type_name, "children": r.child_count}
            for r in (top_nodes if filtering else tree.roots)
        ]
        report.nodes = node_dicts

        struct = self.standard.evaluate(tree)
        misplaced = struct.misplaced
        if not filtering:
            report.structure_compliance = struct.compliance
        else:
            misplaced = [f for f in misplaced if f.guid in active_guids]
            correct = [f for f in struct.correct if f.guid in active_guids]
            total = len(misplaced) + len(correct)
            report.structure_compliance = (
                len(correct) / float(total) if total else 1.0)
        report.misplaced = [
            {"name": f.name, "category": f.category,
             "current": f.current_group, "expected": f.expected_group}
            for f in misplaced
        ]
        return report
