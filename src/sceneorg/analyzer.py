"""SceneAnalyzer: aggregates a SceneTree into a report (pure)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from . import model, naming, translations
from .structure import StructureStandard, default_standard


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
        }


class SceneAnalyzer:
    def __init__(self, standard: StructureStandard = None) -> None:
        self.standard = standard or default_standard()

    def analyze(self, tree: model.SceneTree, file_name: str = "") -> SceneReport:
        report = SceneReport(file=file_name)

        types: Counter = Counter()
        categories: Counter = Counter()
        casing: Counter = Counter()
        language: Counter = Counter()
        light_groups: Counter = Counter()
        camera_groups: Counter = Counter()
        polys_by_cat: Counter = Counter()
        polys_by_group: Counter = Counter()
        node_dicts: list[dict] = []
        assets: list[tuple] = []   # (polys, guid, name, type, points) for the ranking
        total_points = 0
        total_polys = 0
        max_depth = 0
        count = 0

        # ONE pass over all nodes: casing/language per object only once.
        for n in tree.walk():
            count += 1
            if n.depth > max_depth:
                max_depth = n.depth
            cas = naming.detect_casing(n.name).value
            lang = naming.detect_language(
                n.name, translations.DE_WORDS, translations.EN_WORDS)

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

            node_dicts.append({
                "guid": n.guid,
                "name": n.name, "type": n.type_name, "category": n.category,
                "depth": n.depth, "path": n.path, "casing": cas,
                "language": lang, "children": n.child_count,
                "points": n.point_count, "polygons": n.poly_count,
            })

        report.object_count = count
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
        report.top_level = [
            {"name": r.name, "type": r.type_name, "children": r.child_count}
            for r in tree.roots
        ]
        report.nodes = node_dicts

        struct = self.standard.evaluate(tree)
        report.structure_compliance = struct.compliance
        report.misplaced = [
            {"name": f.name, "category": f.category,
             "current": f.current_group, "expected": f.expected_group}
            for f in struct.misplaced
        ]
        return report
