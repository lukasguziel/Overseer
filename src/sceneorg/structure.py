"""Struktur-Standard: erwartete Top-Level-Gruppen + Bewertung (rein)."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import model, naming, translations


@dataclass
class GroupRule:
    """Eine Ziel-Gruppe (Top-Level-Null) und wie Objekte ihr zugeordnet werden.

    match_categories  Objekt-Kategorien, die hierher gehoeren (z.B. {'light'})
    match_keywords    englische Namens-Tokens, die hierher routen
    aliases           alternative Container-Namen (z.B. 'Moebel' == 'Furniture')
    priority          hoehere Prioritaet gewinnt bei mehreren Treffern
    """

    name: str
    match_categories: set = field(default_factory=set)
    match_keywords: set = field(default_factory=set)
    aliases: set = field(default_factory=set)
    priority: int = 0

    def matches(self, node: model.SceneNode) -> bool:
        if node.category in self.match_categories:
            return True
        # Tokens ins Englische uebersetzen -> sprachunabhaengiges Matching
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
    """Regelwerk fuer die gewuenschte Szenen-Gliederung."""

    def __init__(self, rules: list[GroupRule]) -> None:
        # nach Prioritaet absteigend, damit spezifische Regeln zuerst greifen
        self.rules = sorted(rules, key=lambda r: -r.priority)
        # Alias/Name (klein) -> kanonischer Gruppenname
        self._canonical: dict[str, str] = {}
        for r in self.rules:
            self._canonical[r.name.lower()] = r.name
            for a in r.aliases:
                self._canonical[a.lower()] = r.name

    @property
    def group_names(self) -> list[str]:
        return [r.name for r in self.rules]

    def canonical_group(self, name: str | None) -> str | None:
        """Bildet einen tatsaechlichen Container-Namen auf den Kanon ab."""
        if name is None:
            return None
        return self._canonical.get(name.lower())

    def target_group_for(self, node: model.SceneNode) -> str | None:
        for rule in self.rules:
            if rule.matches(node):
                return rule.name
        return None

    def is_group_container(self, node: model.SceneNode) -> bool:
        """Ist dieser Knoten selbst ein (erkannter) Gruppen-Container?

        Anders als frueher NICHT auf die Wurzel beschraenkt: der User darf
        Gruppen verschachteln (z.B. Scene > Lights, House > Furniture). Ein
        Null, dessen Name/Alias auf eine Regel matcht, gilt auf jeder Ebene als
        Container.
        """
        return (node.category == model.CAT_NULL
                and self.canonical_group(node.name) is not None)

    def enclosing_group(self, node: model.SceneNode) -> str | None:
        """Kanonischer Name des NAECHSTGELEGENEN Vorfahren, der ein erkannter
        Gruppen-Container ist -- oder None, wenn das Objekt in keiner erkannten
        Gruppe steckt (also relativ zu den Regeln 'lose' ist).

        Das ist der Kern der hierarchie-bewussten Bewertung: ein Licht in
        Scene > Lights > Interior liegt korrekt (Vorfahre 'Lights' == erwartet),
        auch wenn die oberste Wurzel 'Scene' heisst.
        """
        for anc in node.ancestors():
            canon = self.canonical_group(anc.name)
            if canon is not None:
                return canon
        return None

    def evaluate(self, tree: model.SceneTree) -> StructureReport:
        report = StructureReport(known_groups=self.group_names)
        for node in tree.walk():
            if self.is_group_container(node):
                continue
            expected = self.target_group_for(node)
            if expected is None:
                continue
            # Naechstgelegener erkannter Gruppen-Vorfahre (None = lose).
            enclosing = self.enclosing_group(node)
            report.findings.append(
                Finding(
                    guid=node.guid,
                    name=node.name,
                    category=node.category,
                    current_group=enclosing,
                    expected_group=expected,
                    misplaced=(enclosing != expected),
                )
            )
        return report


def default_standard() -> StructureStandard:
    """Minimaler, immer gueltiger Default: nur kategoriebasierte Regeln.

    Cameras/Lights sind ueber die Objekt-Kategorie eindeutig und daher immer
    korrekt. Inhaltliche Gruppen (Furniture/Interior/Exterior o.ae.) werden
    NICHT geraten -- sie kommen aus config.json bzw. dem Node-Editor, passend
    zur jeweiligen Szene.
    """
    return StructureStandard([
        GroupRule("Cameras", match_categories={model.CAT_CAMERA},
                  aliases={"cams", "kameras", "kamera"}, priority=100),
        GroupRule("Lights", match_categories={model.CAT_LIGHT},
                  aliases={"lichter", "licht", "beleuchtung"}, priority=100),
    ])
