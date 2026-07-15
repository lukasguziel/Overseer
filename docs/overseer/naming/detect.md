# detect

Automatic detection of the prevailing naming scheme (pure). Determines the dominant casing style, language, and number padding from a list of object names, producing a suggestion for `NamingConvention`.

## `_CASING_TO_TARGET`
Maps each observed `Casing` to the closest producible target style (e.g. CAPITALIZED and SPACED both vote PASCAL, LOWER votes LOWER_SNAKE, UPPER votes UPPER_SNAKE). `MIXED`/`EMPTY` cast no vote (ambiguous).

## `DetectionResult` (dataclass)
Holds `style`, `language`, `number_pad`, `confidence`, and the raw `casing_distribution` / `language_distribution` counts.

## `detect_style(names)`
Returns `(style, confidence, raw_casing_distribution)`. Counts votes per target style (skipping EMPTY/MIXED); confidence is the winning style's share of all votes. Falls back to `(PASCAL, 0.0, ...)` when there are no votes.

## `detect_language(names)`
Returns `(language, distribution)`. Majority of per-name detections; German wins ties (`de >= en`). When neither German nor English is seen, defaults to English (no translation needed).

## `detect_number_pad(names)`
Returns the most common zero-padding width. Only names whose trailing number starts with a leading zero and has >1 digit count toward padding. Returns 0 when no numbers or no padded numbers exist.

## `detect_convention(names)`
Top-level: filters empty names, combines the three detectors into a `DetectionResult`.
