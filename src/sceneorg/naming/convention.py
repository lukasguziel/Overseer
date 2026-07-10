from __future__ import annotations

import re
from dataclasses import dataclass

from . import casing as naming
from . import translations

_TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+"
                       r"|\d+(?:[.,]\d+)*")

_SEP_ONLY_RE = re.compile(r"^[\s._\-]+$")

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
        keep_separators: bool = False,
        keep_specials: bool = True,
    ) -> None:
        if style not in TARGET_STYLES:
            raise ValueError("Unsupported target style: %s" % style)
        self.style = style
        self.language = language
        self.number_pad = number_pad
        self.apply_numbering = apply_numbering
        self.apply_casing = apply_casing
        self.keep_separators = keep_separators
        self.keep_specials = keep_specials

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
        if not self.apply_numbering:
            return s
        m = re.match(r"^(.*?)(\d+)$", s)
        if not m or not m.group(1):
            return s
        base = m.group(1)
        if base.endswith(".") and len(base) >= 2 and base[-2].isdigit():
            return s
        return base + self._format_number(int(m.group(2)))

    def _normalize_keep(self, stripped: str) -> str:
        matches = list(_TOKEN_RE.finditer(stripped))
        if not matches:
            return stripped
        last = len(matches) - 1
        out: list[str] = [stripped[:matches[0].start()]]
        word_i = 0
        prev_end = matches[0].start()
        for i, m in enumerate(matches):
            if i > 0:
                out.append(stripped[prev_end:m.start()])
            text = m.group(0)
            if text[0].isalpha():
                out.append(self._case_word(self._translate_one(text.lower()),
                                           word_i == 0))
                word_i += 1
            elif self.apply_numbering and i == last and text.isdigit():
                out.append(self._format_number(int(text)))
            else:
                out.append(text)
            prev_end = m.end()
        out.append(stripped[matches[last].end():])
        if word_i == 0:
            return stripped
        return "".join(out)

    def normalize(self, name: str) -> str:
        stripped = name.strip()

        if not self.apply_casing:
            return self._renumber_only(stripped)
        if self.keep_separators:
            return self._normalize_keep(stripped)
        return self._normalize_full(stripped)

    def _normalize_full(self, stripped: str) -> str:
        matches = list(_TOKEN_RE.finditer(stripped))
        if not matches:
            return stripped

        sep = _SEP[self.style]
        last = len(matches) - 1
        out: list[str] = []
        word_i = 0

        if self.keep_specials:
            prefix = stripped[:matches[0].start()]
            if prefix and not _SEP_ONLY_RE.match(prefix):
                out.append(prefix)

        for i, m in enumerate(matches):
            if i > 0:
                gap = stripped[matches[i - 1].end():m.start()]
                if self.keep_specials and gap and not _SEP_ONLY_RE.match(gap):
                    out.append(gap)
                else:
                    out.append(sep)
            text = m.group(0)
            if text[0].isalpha():
                for j, w in enumerate(_TOKEN_RE.findall(naming.split_camel(text))):
                    if j > 0:
                        out.append(sep)
                    out.append(self._case_word(self._translate_one(w.lower()),
                                               word_i == 0))
                    word_i += 1
            elif self.apply_numbering and i == last and text.isdigit():
                out.append(self._format_number(int(text)))
            else:
                out.append(text)

        if self.keep_specials:
            suffix = stripped[matches[last].end():]
            if suffix and not _SEP_ONLY_RE.match(suffix):
                out.append(suffix)

        if word_i == 0:
            return stripped
        return "".join(out)

    def propose(self, name: str) -> RenameProposal:
        return RenameProposal(old=name, new=self.normalize(name))

    def is_compliant(self, name: str) -> bool:
        return self.normalize(name) == name

    def disambiguate(self, base: str, index: int) -> str:
        return base + _NUM_SEP[self.style] + self._format_number(index)
