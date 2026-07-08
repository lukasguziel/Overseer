from __future__ import annotations

import re
from dataclasses import dataclass

from . import casing as naming
from . import translations

# One token = a run of letters (a word) OR a run of digits that may contain
# decimal separators (a number like "2" or "2.1"). Everything else in the name
# is a separator that gets replaced by the target style's separator. Keeping
# numbers -- decimals included -- as verbatim tokens means naming only touches
# casing and never swallows info like the ".1" in "ROCK_UV_2.1".
_TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+"
                       r"|\d+(?:[.,]\d+)*")

TARGET_STYLES = (
    naming.Casing.PASCAL,
    naming.Casing.CAMEL,
    naming.Casing.LOWER_SNAKE,
    naming.Casing.UPPER_SNAKE,
    naming.Casing.KEBAB,
)

_SEP = {
    naming.Casing.PASCAL: "",
    naming.Casing.CAMEL: "",
    naming.Casing.LOWER_SNAKE: "_",
    naming.Casing.UPPER_SNAKE: "_",
    naming.Casing.KEBAB: "-",
}

_NUM_SEP = {
    naming.Casing.PASCAL: "",
    naming.Casing.CAMEL: "",
    naming.Casing.LOWER_SNAKE: "_",
    naming.Casing.UPPER_SNAKE: "_",
    naming.Casing.KEBAB: "-",
}


@dataclass
class RenameProposal:
    old: str
    new: str

    @property
    def changed(self) -> bool:
        return self.old != self.new


class NamingConvention:
    def __init__(
        self,
        style: naming.Casing = naming.Casing.PASCAL,
        language: str | None = naming.LANG_EN,
        number_pad: int = 2,
        apply_numbering: bool = True,
        apply_casing: bool = True,
    ) -> None:
        if style not in TARGET_STYLES:
            raise ValueError("Unsupported target style: %s" % style)
        self.style = style
        self.language = language
        self.number_pad = number_pad
        # When False, existing numbers are left exactly as they are (no zero
        # padding, no reformatting) -- naming then only touches casing.
        self.apply_numbering = apply_numbering
        # When False, casing and separators are left exactly as they are --
        # naming then only touches numbering (if enabled).
        self.apply_casing = apply_casing

    def _translate_one(self, tok: str) -> str:
        if self.language == naming.LANG_EN:
            return translations.to_english(tok)
        if self.language == naming.LANG_DE:
            return translations.to_german(tok)
        return tok

    def _case_word(self, word: str, first: bool) -> str:
        if self.style == naming.Casing.PASCAL:
            return word.capitalize()
        if self.style == naming.Casing.CAMEL:
            return word.lower() if first else word.capitalize()
        if self.style in (naming.Casing.LOWER_SNAKE, naming.Casing.KEBAB):
            return word.lower()
        if self.style == naming.Casing.UPPER_SNAKE:
            return word.upper()
        return word

    def _format_number(self, num: int) -> str:
        if self.number_pad > 0:
            return str(num).zfill(self.number_pad)
        return str(num)

    def _renumber_only(self, s: str) -> str:
        # Keep casing and separators verbatim; only zero-pad a trailing integer.
        if not self.apply_numbering:
            return s
        m = re.match(r"^(.*?)(\d+)$", s)
        if not m or not m.group(1):
            return s
        base = m.group(1)
        if base.endswith(".") and len(base) >= 2 and base[-2].isdigit():
            return s   # part of a decimal (e.g. "2.1") -> leave it
        return base + self._format_number(int(m.group(2)))

    def normalize(self, name: str) -> str:
        stripped = name.strip()

        if not self.apply_casing:
            return self._renumber_only(stripped)
        # Split into word / number tokens (numbers incl. decimals kept whole);
        # every other character is treated as a separator.
        parts = [(m.group(0)[0].isalpha(), m.group(0))
                 for m in _TOKEN_RE.finditer(naming.split_camel(stripped))]
        if not parts:
            return stripped

        sep = _SEP[self.style]
        last = len(parts) - 1
        out: list[str] = []
        word_i = 0
        for i, (is_word, text) in enumerate(parts):
            if is_word:
                out.append(self._case_word(self._translate_one(text.lower()),
                                           word_i == 0))
                word_i += 1
            elif self.apply_numbering and i == last and text.isdigit():
                out.append(self._format_number(int(text)))
            else:
                out.append(text)  # number kept verbatim (decimal safe)

        if word_i == 0:
            return stripped  # numbers/symbols only -> never fabricate a name
        return sep.join(out)

    def propose(self, name: str) -> RenameProposal:
        return RenameProposal(old=name, new=self.normalize(name))

    def is_compliant(self, name: str) -> bool:
        return self.normalize(name) == name

    def disambiguate(self, base: str, index: int) -> str:
        return base + _NUM_SEP[self.style] + self._format_number(index)
