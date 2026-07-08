from __future__ import annotations

from dataclasses import dataclass, field

from ..core import model
from ..naming import casing as naming
from ..naming import translations


@dataclass
class GroupRule:
    name: str
    match_categories: set = field(default_factory=set)
    match_keywords: set = field(default_factory=set)
    aliases: set = field(default_factory=set)
    priority: int = 0
    parent: str | None = None

    @property
    def path(self) -> str:
        return "%s/%s" % (self.parent, self.name) if self.parent else self.name

    def matches(self, node: model.SceneNode) -> bool:
        if node.category in self.match_categories:
            return True
        tokens = {translations.to_english(t) for t in naming.tokenize(node.name)}
        return bool(tokens & self.match_keywords)


@dataclass
class Finding:
    node: model.SceneNode = field(compare=False)
    current_group: str | None = None
    expected_group: str = ""
    misplaced: bool = False

    @property
    def guid(self) -> int:
        return self.node.guid

    @property
    def name(self) -> str:
        return self.node.name

    @property
    def category(self) -> str:
        return self.node.category


@dataclass
class StructureReport:
    findings: list[Finding] = field(default_factory=list)
    known_groups: list[str] = field(default_factory=list)

    @property
    def misplaced(self) -> list[Finding]:
        return [f for f in self.findings if f.misplaced]

    @property
    def correct(self) -> list[Finding]:
        return [f for f in self.findings if not f.misplaced]

    @property
    def compliance(self) -> float:
        if not self.findings:
            return 1.0
        return len(self.correct) / float(len(self.findings))


class StructureStandard:
    def __init__(self, rules: list[GroupRule]) -> None:
        self.rules = sorted(rules, key=lambda r: -r.priority)
        self._canonical: dict[str, str] = {}
        self._rules_by_name: dict[str, list[GroupRule]] = {}
        for r in self.rules:
            for key in {r.name.lower()} | {a.lower() for a in r.aliases}:
                self._canonical.setdefault(key, r.name)
                self._rules_by_name.setdefault(key, []).append(r)

    @property
    def group_names(self) -> list[str]:
        return [r.name for r in self.rules]

    @property
    def group_paths(self) -> list[str]:
        return [r.path for r in self.rules]

    def canonical_group(self, name: str | None) -> str | None:
        if name is None:
            return None
        return self._canonical.get(name.lower())

    def container_rule(self, node: model.SceneNode) -> GroupRule | None:
        if node.category != model.CAT_NULL:
            return None
        candidates = self._rules_by_name.get(node.name.lower())
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]
        enclosing = self.enclosing_group_path(node)
        for r in candidates:
            if r.parent is not None and r.parent == enclosing:
                return r
        for r in candidates:
            if r.parent is None:
                return r
        return candidates[0]

    def target_group_for(self, node: model.SceneNode) -> str | None:
        for rule in self.rules:
            if rule.matches(node):
                return rule.path
        return None

    def is_group_container(self, node: model.SceneNode) -> bool:
        return (node.category == model.CAT_NULL
                and self.canonical_group(node.name) is not None)

    def enclosing_group(self, node: model.SceneNode) -> str | None:
        for anc in node.ancestors():
            canon = self.canonical_group(anc.name)
            if canon is not None:
                return canon
        return None

    def enclosing_group_path(self, node: model.SceneNode) -> str | None:
        for anc in node.ancestors():
            rule = self.container_rule(anc)
            if rule is not None:
                return rule.path
        return None

    @staticmethod
    def path_complies(enclosing: str | None, expected: str) -> bool:
        if enclosing is None:
            return False
        return enclosing == expected or enclosing.startswith(expected + "/")

    def evaluate(self, tree: model.SceneTree) -> StructureReport:
        report = StructureReport(known_groups=self.group_names)
        for node in tree.walk():
            if self.is_group_container(node):
                continue
            expected = self.target_group_for(node)
            if expected is None:
                continue
            enclosing = self.enclosing_group_path(node)
            report.findings.append(
                Finding(
                    node=node,
                    current_group=enclosing,
                    expected_group=expected,
                    misplaced=not self.path_complies(enclosing, expected),
                )
            )
        return report


def default_standard() -> StructureStandard:
    return StructureStandard([
        GroupRule("Cameras", match_categories={model.CAT_CAMERA},
                  aliases={"cams", "kameras", "kamera"}, priority=100),
        GroupRule("Lights", match_categories={model.CAT_LIGHT},
                  aliases={"lichter", "licht", "beleuchtung"}, priority=100),
    ])
