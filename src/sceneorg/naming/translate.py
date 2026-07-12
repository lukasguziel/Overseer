from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import casing as naming
from . import translations

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

AMBIGUOUS_DE = {
    "bad", "wand", "regal", "hand", "arm", "hut", "tag", "rat", "gift",
    "kind", "boden", "hof", "brief", "hell", "bald", "not", "war", "die",
    "man", "fast", "gut", "rock", "stern",
}

LANG_CHARS = {
    "de": "äöüß",
    "fr": "éèêëàâçîïôûùœ",
    "es": "áéíóúñü¡¿",
    "it": "àèéìòù",
    "nl": "ĳ",
    "pl": "ąćęłńśźż",
    "cs": "čďěňřšťůž",
    "pt": "ãõçáâêôà",
    "tr": "ğşıİ",
    "ru": "абвгдежзийклмнопрстуфхцчшщъыьэюя",
}


@dataclass
class TranslateProposal:
    node: object = field(compare=False)
    new: str = ""
    words: list = field(default_factory=list)
    lang: str = naming.LANG_UNKNOWN

    @property
    def guid(self) -> int:
        return self.node.guid

    @property
    def old(self) -> str:
        return self.node.name


def _match_case(src: str, tgt: str) -> str:
    if src.isupper():
        return tgt.upper()
    if src.islower():
        return tgt.lower()
    if src[:1].isupper() and src[1:].islower():
        return tgt.capitalize()
    return tgt


def _evidence_langs(name: str) -> set[str]:
    low = name.lower()
    out: set[str] = set()
    for lang, chars in LANG_CHARS.items():
        if any(ch in low for ch in chars):
            out.add(lang)
    for tok in _WORD.findall(low):
        lang = translations.UNIQUE_LANG.get(tok)
        if lang is None:
            alt = translations._deumlauted(tok)
            if alt != tok and translations.UNIQUE_LANG.get(alt) == "de":
                lang = "de"
        if lang is not None and tok not in AMBIGUOUS_DE:
            out.add(lang)
    return out


def _has_german_evidence(name: str) -> bool:
    return "de" in _evidence_langs(name)


def detect_name_language(name: str) -> str:
    low = name.lower()
    evidence = _evidence_langs(name)
    if len(evidence) == 1:
        return next(iter(evidence))
    votes: dict[str, int] = {}
    en = 0
    for tok in _WORD.findall(low):
        for lang in translations.BULK_LANGS:
            if tok in translations.WORDS[lang]:
                votes[lang] = votes.get(lang, 0) + 1
        if tok in translations.EN_WORDS:
            en += 1
    if evidence:
        best = max(evidence, key=lambda lg: votes.get(lg, 0))
        return best
    if votes:
        lang, n = max(votes.items(), key=lambda kv: kv[1])
        if n > en:
            return lang
    if en:
        return naming.LANG_EN
    return naming.LANG_UNKNOWN


def translate_preserving(name: str, target: str = naming.LANG_EN,
                         ) -> tuple[str, list]:
    changed: list = []
    if target == naming.LANG_DE:
        def repl_de(m: re.Match) -> str:
            word = m.group(0)
            tgt = translations.to_german(word.lower())
            if tgt == word.lower():
                return word
            cased = _match_case(word, tgt)
            changed.append((word, cased))
            return cased
        return _WORD.sub(repl_de, name), changed

    evidence = _evidence_langs(name)

    def repl(m: re.Match) -> str:
        word = m.group(0)
        low = word.lower()
        candidates = translations.candidate_langs(low)
        if not candidates:
            tgt = translations.to_english(low, include_ambiguous=False)
            if tgt != low and ("de" in evidence
                               or low in translations.UNIQUE_LANG):
                cased = _match_case(word, tgt)
                changed.append((word, cased))
                return cased
            return word
        pick = None
        for lang in translations.BULK_LANGS:
            if lang in candidates and lang in evidence:
                pick = lang
                break
        if pick is None:
            unique = translations.UNIQUE_LANG.get(low)
            if unique in candidates and low not in AMBIGUOUS_DE:
                pick = unique
        if pick is None:
            return word
        if pick == "de" and low in AMBIGUOUS_DE and "de" not in evidence:
            return word
        tgt = translations.lookup_en(low, pick, include_ambiguous=True)
        if not tgt or tgt == low:
            return word
        cased = _match_case(word, tgt)
        changed.append((word, cased))
        return cased

    new = _WORD.sub(repl, name)
    return new, changed


# Words shorter than this are left alone: a lone "a" or "x" is an index or an
# axis, never a word worth translating.
MIN_WORD = 2


def translatable_words(name: str) -> list[str]:
    """The words inside an object name, lowercased, in order.

    Object names are not sentences: "body_rear_wing_part_usm.1" is five words
    glued together with separators plus a code and an index. A translator fed
    the raw name recognizes nothing — fed the WORDS it recognizes almost all
    of them.
    """
    return [w.lower() for w in _WORD.findall(name) if len(w) >= MIN_WORD]


def rebuild_with(name: str, mapping: dict) -> tuple[str, list]:
    """Put translated words back into the name, keeping everything else.

    Separators, digits, codes and the casing of each word survive — only the
    words the mapping knows are swapped, so "Body_Rear_Wing.1" stays
    "<Word>_<Word>_<Word>.1" in the target language.
    """
    changed: list = []

    def repl(m: re.Match) -> str:
        word = m.group(0)
        tgt = str(mapping.get(word.lower()) or "").strip()
        if not tgt or tgt.lower() == word.lower():
            return word
        cased = _match_case(word, tgt)
        changed.append((word, cased))
        return cased

    return _WORD.sub(repl, name), changed


def plan_translations(tree, scope: set | None = None,
                      target: str = naming.LANG_EN) -> list[TranslateProposal]:
    out: list[TranslateProposal] = []
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        new, words = translate_preserving(n.name, target)
        if words and new != n.name:
            out.append(TranslateProposal(
                node=n, new=new, words=words,
                lang=detect_name_language(n.name)))
    return out


@dataclass
class LanguageSummary:
    counts: dict = field(default_factory=dict)
    total: int = 0
    dominant: str = naming.LANG_UNKNOWN

    @property
    def de(self) -> int:
        return self.counts.get("de", 0)

    @property
    def en(self) -> int:
        return self.counts.get("en", 0)

    @property
    def unknown(self) -> int:
        return self.counts.get("unknown", 0)

    def to_dict(self) -> dict:
        return {"counts": dict(self.counts), "total": self.total,
                "dominant": self.dominant,
                "de": self.de, "en": self.en, "unknown": self.unknown}


def detect_languages(tree, scope: set | None = None) -> LanguageSummary:
    s = LanguageSummary()
    for n in tree.walk():
        if scope is not None and n.guid not in scope:
            continue
        lang = detect_name_language(n.name)
        s.total += 1
        s.counts[lang] = s.counts.get(lang, 0) + 1

    ranked = sorted(s.counts.items(), key=lambda kv: kv[1], reverse=True)
    if ranked and (len(ranked) == 1 or ranked[0][1] > ranked[1][1]):
        s.dominant = ranked[0][0]
    else:
        s.dominant = naming.LANG_UNKNOWN
    return s
