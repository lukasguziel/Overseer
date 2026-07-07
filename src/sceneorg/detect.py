"""Automatic detection of the prevailing naming scheme (pure).

Determines the dominant casing style, language and number padding from a
list of object names -> suggestion for the NamingConvention.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from . import naming, translations
from .naming import Casing

# Observed casings -> closest producible target style (TARGET_STYLES).
_CASING_TO_TARGET = {
    Casing.PASCAL: Casing.PASCAL,
    Casing.CAPITALIZED: Casing.PASCAL,
    Casing.SPACED: Casing.PASCAL,
    Casing.CAMEL: Casing.CAMEL,
    Casing.LOWER_SNAKE: Casing.LOWER_SNAKE,
    Casing.LOWER: Casing.LOWER_SNAKE,
    Casing.UPPER_SNAKE: Casing.UPPER_SNAKE,
    Casing.UPPER: Casing.UPPER_SNAKE,
    Casing.KEBAB: Casing.KEBAB,
    # MIXED / EMPTY: no vote (ambiguous)
}

_NUM_SUFFIX = re.compile(r"(\d+)$")


@dataclass
class DetectionResult:
    style: Casing = Casing.PASCAL
    language: str | None = naming.LANG_EN
    number_pad: int = 2
    confidence: float = 0.0
    casing_distribution: dict[str, int] = field(default_factory=dict)
    language_distribution: dict[str, int] = field(default_factory=dict)


def detect_style(names: list[str]) -> tuple[Casing, float, dict[str, int]]:
    raw = Counter()
    votes = Counter()
    for name in names:
        c = naming.detect_casing(name)
        if c in (Casing.EMPTY, Casing.MIXED):
            continue
        raw[c.value] += 1
        target = _CASING_TO_TARGET.get(c)
        if target is not None:
            votes[target] += 1
    if not votes:
        return Casing.PASCAL, 0.0, dict(raw)
    style, top = votes.most_common(1)[0]
    confidence = top / float(sum(votes.values()))
    return style, confidence, dict(raw)


def detect_language(names: list[str]) -> tuple[str, dict[str, int]]:
    dist = Counter()
    for name in names:
        dist[naming.detect_language(name, translations.DE_WORDS, translations.EN_WORDS)] += 1
    de = dist.get(naming.LANG_DE, 0)
    en = dist.get(naming.LANG_EN, 0)
    if de == 0 and en == 0:
        return naming.LANG_EN, dict(dist)  # default, no translation needed
    return (naming.LANG_DE if de >= en else naming.LANG_EN), dict(dist)


def detect_number_pad(names: list[str]) -> int:
    padded = Counter()
    any_number = 0
    for name in names:
        m = _NUM_SUFFIX.search(name.strip())
        if not m:
            continue
        any_number += 1
        digits = m.group(1)
        if len(digits) > 1 and digits[0] == "0":
            padded[len(digits)] += 1
    if any_number == 0 or not padded:
        return 0
    return padded.most_common(1)[0][0]


def detect_convention(names: list[str]) -> DetectionResult:
    names = [n for n in names if n and n.strip()]
    style, conf, casing_dist = detect_style(names)
    lang, lang_dist = detect_language(names)
    pad = detect_number_pad(names)
    return DetectionResult(
        style=style,
        language=lang,
        number_pad=pad,
        confidence=conf,
        casing_distribution=casing_dist,
        language_distribution=lang_dist,
    )
