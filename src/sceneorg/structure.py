"""Structure standard: expected top-level groups + evaluation (pure)."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import model, naming, translations


@dataclass
class GroupRule:
    """A target group (null container) and how objects are assigned to it.

    match_categories  object categories that belong here (e.g. {'light'})
    match_keywords    English name tokens that route here
    aliases           alternative container names (e.g. 'Moebel' == 'Furniture')
    priority          higher priority wins when multiple rules match
    parent            path of the parent group ('Room' or 'Room/Furniture');
                      None = top-level group
    """

    name: str
    match_categories: set = field(default_factory=set)
    match_keywords: set = field(default_factory=set)
    aliases: set = field(default_factory=set)
    priority: int = 0
    parent: str | None = None

    @property
    def path(self) -> str:
        """Full group path, e.g. 'Room/Furniture'."""
        return "%s/%s" % (self.parent, self.name) if self.parent else self.name

    def matches(self, node: model.SceneNode) -> bool:
        if node.category in self.match_categories:
            return True
        # Translate tokens to English -> language-independent matching
        tokens = {translations.to_english(t) for t in naming.tokenize(node.name)}
        return bool(tokens & self.match_keywords)


@dataclass
class Finding:
    guid: int
    name: str
    category: str
    current_group: str | None
    expected_group: str
    misplaced: bool = False


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
    """Rule set for the desired scene organization."""

    def __init__(self, rules: list[GroupRule]) -> None:
        # sorted by priority descending so specific rules apply first
        self.rules = sorted(rules, key=lambda r: -r.priority)
        # alias/name (lowercase) -> canonical group name (first = highest prio)
        self._canonical: dict[str, str] = {}
        # alias/name (lowercase) -> all rules carrying that name/alias
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
        """Maps an actual container name to the canonical one."""
        if name is None:
            return None
        return self._canonical.get(name.lower())

    def container_rule(self, node: model.SceneNode) -> GroupRule | None:
        """The rule this container node represents, parent-chain aware.

        If several rules share a name (e.g. 'Lights' under 'Room' and under
        'Studio'), the one whose parent path matches the container's own
        enclosing group wins; a top-level rule matches anywhere.
        """
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
        """Target group PATH for an object (e.g. 'Room/Furniture')."""
        for rule in self.rules:
            if rule.matches(node):
                return rule.path
        return None

    def is_group_container(self, node: model.SceneNode) -> bool:
        """Is this node itself a (recognized) group container?

        Unlike before, NOT restricted to the root: the user may nest groups
        (e.g. Scene > Lights, House > Furniture). A null whose name/alias
        matches a rule counts as a container at any level.
        """
        return (node.category == model.CAT_NULL
                and self.canonical_group(node.name) is not None)

    def enclosing_group(self, node: model.SceneNode) -> str | None:
        """Canonical name of the NEAREST ancestor that is a recognized group
        container -- or None if the object sits in no recognized group
        (i.e. it is 'loose' relative to the rules).

        This is the core of the hierarchy-aware evaluation: a light in
        Scene > Lights > Interior is placed correctly (ancestor 'Lights' ==
        expected), even if the topmost root is called 'Scene'.
        """
        for anc in node.ancestors():
            canon = self.canonical_group(anc.name)
            if canon is not None:
                return canon
        return None

    def enclosing_group_path(self, node: model.SceneNode) -> str | None:
        """Group PATH of the nearest recognized ancestor container.

        Like enclosing_group(), but returns the rule's full path
        ('Room/Furniture') so nested standards evaluate correctly.
        """
        for anc in node.ancestors():
            rule = self.container_rule(anc)
            if rule is not None:
                return rule.path
        return None

    @staticmethod
    def path_complies(enclosing: str | None, expected: str) -> bool:
        """A node complies if it sits in the expected group or deeper below it
        (a light under Lights/Interior still counts for 'Lights')."""
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
            # Nearest recognized group ancestor path (None = loose).
            enclosing = self.enclosing_group_path(node)
            report.findings.append(
                Finding(
                    guid=node.guid,
                    name=node.name,
                    category=node.category,
                    current_group=enclosing,
                    expected_group=expected,
                    misplaced=not self.path_complies(enclosing, expected),
                )
            )
        return report


def default_standard() -> StructureStandard:
    """Minimal, always-valid default: category-based rules only.

    Cameras/Lights are unambiguous via the object category and therefore
    always correct. Content groups (Furniture/Interior/Exterior etc.) are
    NOT guessed -- they come from config.json or the node editor, tailored
    to the specific scene.
    """
    return StructureStandard([
        GroupRule("Cameras", match_categories={model.CAT_CAMERA},
                  aliases={"cams", "kameras", "kamera"}, priority=100),
        GroupRule("Lights", match_categories={model.CAT_LIGHT},
                  aliases={"lichter", "licht", "beleuchtung"}, priority=100),
    ])
