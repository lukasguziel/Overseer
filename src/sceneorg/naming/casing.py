"""Pure naming analysis: tokenizer, casing detection, language heuristic."""

from __future__ import annotations

import re
from enum import Enum


class Casing(str, Enum):
    EMPTY = "empty"
    UPPER_SNAKE = "UPPER_SNAKE"      # LIGHT_KEY_01
    LOWER_SNAKE = "lower_snake"      # light_key_01
    KEBAB = "kebab"                  # light-key
    CAMEL = "camelCase"             # lightKey
    PASCAL = "PascalCase"           # LightKey
    UPPER = "UPPER"                  # LIGHT
    LOWER = "lower"                  # light
    CAPITALIZED = "Capitalized"      # Light
    SPACED = "spaced"                # Light Key
    MIXED = "mixed"


_RE_CAMEL = re.compile(r"^[a-z][a-z0-9]*([A-Z][a-z0-9]*)+$")
_RE_PASCAL = re.compile(r"^[A-Z][a-z0-9]*([A-Z][a-z0-9]*)+$")
_RE_UPPER_SNAKE = re.compile(r"^[A-Z0-9]+(_[A-Z0-9]+)+$")
_RE_LOWER_SNAKE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)+$")
_RE_SPLIT = re.compile(r"[\s_\-\.]+")
_RE_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_RE_NUM_SUFFIX = re.compile(r"^(.*?)[ _\-]*?(\d+)$")


def split_camel(name: str) -> str:
    """Inserts a space before uppercase boundaries (fooBar -> foo Bar)."""
    return _RE_CAMEL_BOUNDARY.sub(r"\1 \2", name)


def tokenize(name: str) -> list[str]:
    """Splits a name into lowercase word tokens (pure numbers dropped)."""
    spaced = split_camel(name)
    parts = _RE_SPLIT.split(spaced)
    out = []
    for p in parts:
        if not p:
            continue
        if any(ch.isalpha() for ch in p):
            out.append(p.lower())
    return out


def split_trailing_number(name: str) -> tuple[str, int | None]:
    """Splits off a trailing number: 'Chair 01' -> ('Chair', 1)."""
    m = _RE_NUM_SUFFIX.match(name.strip())
    if not m:
        return name.strip(), None
    base, num = m.group(1), m.group(2)
    if not base:
        return name.strip(), None
    return base.strip(" _-"), int(num)


def detect_casing(name: str) -> Casing:
    base = name.strip()
    if not base:
        return Casing.EMPTY
    if " " in base:
        return Casing.SPACED
    if _RE_UPPER_SNAKE.match(base):
        return Casing.UPPER_SNAKE
    if _RE_LOWER_SNAKE.match(base):
        return Casing.LOWER_SNAKE
    if "-" in base:
        return Casing.KEBAB
    # Check single-word cases BEFORE the camel/pascal regexes:
    # "LIGHT" would otherwise be misdetected as PascalCase.
    if base.isupper():
        return Casing.UPPER
    if base.islower():
        return Casing.LOWER
    if _RE_CAMEL.match(base):
        return Casing.CAMEL
    if _RE_PASCAL.match(base):
        return Casing.PASCAL
    if base[0].isupper() and base[1:].islower():
        return Casing.CAPITALIZED
    return Casing.MIXED


# -- Language heuristic ---------------------------------------------------

LANG_DE = "de"
LANG_EN = "en"
LANG_UNKNOWN = "unknown"

_UMLAUTS = "äöüß"


def detect_language(name: str, de_words: set, en_words: set) -> str:
    low = name.lower()
    de = en = 0
    for tok in tokenize(name):
        if tok in de_words:
            de += 1
        if tok in en_words:
            en += 1
    if any(ch in low for ch in _UMLAUTS):
        de += 1
    if de > en:
        return LANG_DE
    if en > de:
        return LANG_EN
    return LANG_UNKNOWN
