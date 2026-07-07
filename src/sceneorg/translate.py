"""Translation tool: detects non-English object names and proposes a
casing-preserving translation (pure, no c4d).

Unlike the NamingConvention, casing is NOT unified here: each German word is
replaced in place by its English counterpart, while the original's
upper-/lowercase pattern, separators and trailing numbers are preserved.
This lets the user decide per object.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import translations

# Word runs incl. umlauts; everything else (digits, _, -, spaces) stays.
_WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")


@dataclass
class TranslateProposal:
    guid: int
    old: str
    new: str
    words: list  # [(german, english), ...] that were actually replaced


def _match_case(src: str, tgt: str) -> str:
    """Transfers the casing pattern from src to the translation tgt."""
    if src.isupper():
        return tgt.upper()
    if src.islower():
        return tgt.lower()
    if src[:1].isupper() and src[1:].islower():
        return tgt.capitalize()
    return tgt


def translate_preserving(name: str) -> tuple[str, list]:
    """Translates German words in the name, keeps casing/structure.

    Returns (new_name, [(de, en), ...]). The list is empty if nothing was
    translatable (the name then counts as 'already English / unknown').
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
    """Proposals for all objects with translatable (German) names."""
    out: list[TranslateProposal] = []
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        new, words = translate_preserving(n.name)
        if words and new != n.name:
            out.append(TranslateProposal(guid=n.guid, old=n.name, new=new, words=words))
    return out
