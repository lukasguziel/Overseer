from __future__ import annotations

import re
from dataclasses import dataclass

from . import casing as naming
from . import translations

_WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+")

AMBIGUOUS_DE = {
    "bad", "wand", "regal", "hand", "arm", "hut", "tag", "rat", "gift",
    "kind", "boden", "hof", "brief", "hell", "bald", "not", "war", "die",
    "man", "fast", "gut", "rock", "stern",
}

_UMLAUTS = "äöüß"


@dataclass
class TranslateProposal:
    guid: int
    old: str
    new: str
    words: list
    lang: str = naming.LANG_UNKNOWN


def _match_case(src: str, tgt: str) -> str:
    if src.isupper():
        return tgt.upper()
    if src.islower():
        return tgt.lower()
    if src[:1].isupper() and src[1:].islower():
        return tgt.capitalize()
    return tgt


def detect_name_language(name: str) -> str:
    return naming.detect_language(name, translations.DE_WORDS,
                                  translations.EN_WORDS)


def _has_german_evidence(name: str) -> bool:
    low = name.lower()
    if any(ch in low for ch in _UMLAUTS):
        return True
    for tok in _WORD.findall(low):
        if tok in translations.DE_WORDS and tok not in AMBIGUOUS_DE:
            return True
    return False


def translate_preserving(name: str, target: str = naming.LANG_EN) -> tuple[str, list]:
    changed: list = []
    if target == naming.LANG_DE:
        lookup = translations.to_german
        guarded = False
        evidence = True
    else:
        lookup = translations.to_english
        guarded = True
        evidence = _has_german_evidence(name)
    ambiguous = AMBIGUOUS_DE & translations.DE_WORDS if guarded else set()

    def repl(m: re.Match) -> str:
        word = m.group(0)
        low = word.lower()
        tgt = lookup(low)
        if tgt == low:
            return word
        if low in ambiguous and not evidence:
            return word
        cased = _match_case(word, tgt)
        changed.append((word, cased))
        return cased

    new = _WORD.sub(repl, name)
    return new, changed


def plan_translations(tree, scope: set | None = None,
                      target: str = naming.LANG_EN) -> list[TranslateProposal]:
    out: list[TranslateProposal] = []
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        new, words = translate_preserving(n.name, target)
        if words and new != n.name:
            out.append(TranslateProposal(
                guid=n.guid, old=n.name, new=new, words=words,
                lang=detect_name_language(n.name)))
    return out


@dataclass
class LanguageSummary:
    de: int = 0
    en: int = 0
    unknown: int = 0
    total: int = 0
    dominant: str = naming.LANG_UNKNOWN

    def to_dict(self) -> dict:
        return {"de": self.de, "en": self.en, "unknown": self.unknown,
                "total": self.total, "dominant": self.dominant}


def detect_languages(tree, scope: set | None = None) -> LanguageSummary:
    s = LanguageSummary()
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        lang = detect_name_language(n.name)
        s.total += 1
        if lang == naming.LANG_DE:
            s.de += 1
        elif lang == naming.LANG_EN:
            s.en += 1
        else:
            s.unknown += 1

    if s.de > s.en and s.de > s.unknown:
        s.dominant = naming.LANG_DE
    elif s.en > s.de and s.en > s.unknown:
        s.dominant = naming.LANG_EN
    else:
        s.dominant = naming.LANG_UNKNOWN
    return s
