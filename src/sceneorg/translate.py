"""Uebersetzungs-Tool: erkennt nicht-englische Objektnamen und schlaegt eine
casing-erhaltende Uebersetzung vor (rein, kein c4d).

Anders als die NamingConvention wird hier NICHT das Casing vereinheitlicht:
jedes deutsche Wort wird an Ort und Stelle durch sein englisches Pendant
ersetzt, wobei Gross-/Kleinschreibung, Trenner und abschliessende Zahlen des
Originals erhalten bleiben. So kann der User pro Objekt entscheiden.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import translations

# Wort-Runs inkl. Umlauten; alles andere (Zahlen, _, -, Leerzeichen) bleibt.
_WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")


@dataclass
class TranslateProposal:
    guid: int
    old: str
    new: str
    words: list  # [(deutsch, englisch), ...] die tatsaechlich ersetzt wurden


def _match_case(src: str, tgt: str) -> str:
    """Uebertraegt das Casing-Muster von src auf die Uebersetzung tgt."""
    if src.isupper():
        return tgt.upper()
    if src.islower():
        return tgt.lower()
    if src[:1].isupper() and src[1:].islower():
        return tgt.capitalize()
    return tgt


def translate_preserving(name: str) -> tuple[str, list]:
    """Uebersetzt deutsche Woerter im Namen, behaelt Casing/Struktur.

    Gibt (neuer_name, [(de, en), ...]) zurueck. Die Liste ist leer, wenn nichts
    uebersetzbar war (Name gilt dann als 'schon englisch / unbekannt').
    """
    changed: list = []

    def repl(m: re.Match) -> str:
        word = m.group(0)
        en = translations.to_english(word.lower())
        if en != word.lower():
            cased = _match_case(word, en)
            changed.append((word, cased))
            return cased
        return word

    new = _WORD.sub(repl, name)
    return new, changed


def plan_translations(tree, scope: set | None = None) -> list[TranslateProposal]:
    """Vorschlaege fuer alle Objekte mit uebersetzbaren (deutschen) Namen."""
    out: list[TranslateProposal] = []
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        new, words = translate_preserving(n.name)
        if words and new != n.name:
            out.append(TranslateProposal(guid=n.guid, old=n.name, new=new, words=words))
    return out
