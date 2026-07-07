"""NamingConvention: normalizes object names to a uniform scheme (pure)."""

from __future__ import annotations

from dataclasses import dataclass

from . import naming, translations

# Target casings the convention can produce.
TARGET_STYLES = (
    naming.Casing.PASCAL,
    naming.Casing.CAMEL,
    naming.Casing.LOWER_SNAKE,
    naming.Casing.UPPER_SNAKE,
    naming.Casing.KEBAB,
)

# Separator per target style (for word joints).
_SEP = {
    naming.Casing.PASCAL: "",
    naming.Casing.CAMEL: "",
    naming.Casing.LOWER_SNAKE: "_",
    naming.Casing.UPPER_SNAKE: "_",
    naming.Casing.KEBAB: "-",
}

# Separator before a trailing number.
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
    """Configurable naming scheme.

    Parameters
    ----------
    style           target casing (Casing.PASCAL etc.)
    language        target language 'en' / 'de' / None (no translation)
    number_pad      zero padding for trailing numbers (0 = off)
    """

    def __init__(
        self,
        style: naming.Casing = naming.Casing.PASCAL,
        language: str | None = naming.LANG_EN,
        number_pad: int = 2,
    ) -> None:
        if style not in TARGET_STYLES:
            raise ValueError("Unsupported target style: %s" % style)
        self.style = style
        self.language = language
        self.number_pad = number_pad

    # -- Word transformation -----------------------------------------------
    def _translate(self, tokens: list[str]) -> list[str]:
        if self.language == naming.LANG_EN:
            return [translations.to_english(t) for t in tokens]
        if self.language == naming.LANG_DE:
            return [translations.to_german(t) for t in tokens]
        return tokens

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

    # -- Public API ---------------------------------------------------------
    def normalize(self, name: str) -> str:
        base, num = naming.split_trailing_number(name)
        tokens = naming.tokenize(base)
        tokens = self._translate(tokens)
        tokens = [t for t in tokens if t]
        if not tokens:
            # Number only / empty -> do not break the original name
            return name.strip()

        sep = _SEP[self.style]
        words = [self._case_word(t, i == 0) for i, t in enumerate(tokens)]
        core = sep.join(words)

        if num is not None:
            return core + _NUM_SEP[self.style] + self._format_number(num)
        return core

    def propose(self, name: str) -> RenameProposal:
        return RenameProposal(old=name, new=self.normalize(name))

    def is_compliant(self, name: str) -> bool:
        return self.normalize(name) == name

    def disambiguate(self, base: str, index: int) -> str:
        """Appends a disambiguating counter in the target style."""
        return base + _NUM_SEP[self.style] + self._format_number(index)
