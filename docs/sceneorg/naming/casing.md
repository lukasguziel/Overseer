# casing

Pure naming analysis: tokenizer, casing detection, and a language heuristic. No `c4d` imports.

## `Casing` (Enum)
String enum of casing styles. Producible/target styles plus purely observable ones: `EMPTY`, `UPPER_SNAKE` (LIGHT_KEY_01), `LOWER_SNAKE` (light_key_01), `KEBAB` (light-key), `CAMEL` (lightKey), `PASCAL` (LightKey), `UPPER` (LIGHT), `LOWER` (light), `CAPITALIZED` (Light), `SPACED` (Light Key), `MIXED`.

## `split_camel(name)`
Inserts a space before uppercase boundaries (`fooBar` -> `foo Bar`).

## `tokenize(name, keep_numbers=False)`
Splits a name into lowercase tokens. Splits on whitespace/underscore/hyphen/dot and camel boundaries. By default pure-number tokens are dropped (only tokens with at least one alpha char survive) — right for keyword/language matching. With `keep_numbers=True` standalone digit tokens are kept too; `NamingConvention.normalize` uses this so a number in a name (e.g. the `1` in `-1 Basement`) is not lost during a casing-only rename.

## `split_trailing_number(name)`
Splits off a trailing number: `'Chair 01'` -> `('Chair', 1)`. Returns `(name, None)` when there is no trailing number, or when stripping the number would leave an empty base (number-only names stay intact).

## `detect_casing(name)`
Classifies a single name into a `Casing`. Gotcha: single-word `UPPER`/`LOWER` cases are checked BEFORE the camel/pascal regexes, otherwise `"LIGHT"` would be misdetected as PascalCase. Spaced names short-circuit early.

## Language heuristic
Constants `LANG_DE`, `LANG_EN`, `LANG_UNKNOWN`. `detect_language(name, de_words, en_words)` counts tokens found in the German vs. English word sets; presence of an umlaut (`äöüß`) adds a German vote. Returns the majority language, or `LANG_UNKNOWN` on a tie.
