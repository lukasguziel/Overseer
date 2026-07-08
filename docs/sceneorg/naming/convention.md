# convention

`NamingConvention`: normalizes object names to a uniform scheme (pure). Pipeline: tokenize -> optional translate -> case -> padded trailing number. Idempotent.

## `TARGET_STYLES`
The casings the convention can actually produce: PASCAL, CAMEL, LOWER_SNAKE, UPPER_SNAKE, KEBAB. `_SEP` maps each to its word-joint separator and `_NUM_SEP` to the separator placed before a trailing number.

## `RenameProposal` (dataclass)
`old` / `new` pair. Property `changed` is `True` when they differ.

## `NamingConvention`
Configurable scheme. Constructor params: `style` (a `Casing`, must be in `TARGET_STYLES` or raises `ValueError`), `language` (`'en'`/`'de'`/`None` for no translation), `number_pad` (zero padding for trailing numbers; 0 = off).

- `normalize(name)`: main entry. Splits trailing number, tokenizes (with `keep_numbers=True`, so leading/inner numbers survive — casing-only renames never drop digits), translates, cases each word, joins with the style separator, re-appends the padded trailing number. If tokenizing leaves nothing (empty), returns the stripped original name unchanged so the name is never broken.
- `propose(name)`: returns a `RenameProposal` wrapping `normalize`.
- `is_compliant(name)`: `True` when the name already equals its normalized form.
- `disambiguate(base, index)`: appends a disambiguating counter in the target style.
