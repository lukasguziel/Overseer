# overseer.core.naming — naming convention engine

Pure, `c4d`-free logic that turns a raw object name into a normalized one:
tokenize -> translate (optional) -> apply casing -> pad trailing number. Every
transform is idempotent (running it twice yields the same name), so it is safe
to re-apply on each pass. Lives at `src/overseer/core/naming/` (an area
package of `core`); no module here imports `c4d` or `bpy`.

## Modules

### __init__.py
Empty package marker.

### casing.py
Low-level string primitives. `Casing` enum (producible + detectable styles),
`tokenize`, `split_camel`, `split_trailing_number`, `detect_casing`,
`detect_language`. Gotcha: `detect_casing` returns richer states (UPPER, LOWER,
CAPITALIZED, SPACED, MIXED) than the five styles the convention can actually
emit — detection maps those onto real targets in `detect.py`.

### convention.py
`NamingConvention` (the workhorse) + `RenameProposal`. `normalize()` branches on
`apply_casing`/`keep_separators` into full, keep-separators, or renumber-only
paths. `_TOKEN_RE` treats decimals ("2.1") as one verbatim number token so info
is never swallowed; only a trailing pure integer gets zero-padded. Gotcha:
names that are numbers/symbols only are returned unchanged (never fabricate a
word); `keep_specials` lets brackets etc. survive full normalization.

### detect.py
Auto-detect an existing scheme from a list of names: `detect_style`,
`detect_language`, `detect_number_pad`, `detect_convention` -> `DetectionResult`
(with confidence + distributions). Gotcha: EMPTY/MIXED casings do not vote;
padding is only inferred from numbers with a leading zero.

### translate.py
Guarded multi-language -> EN (or EN->DE) rename proposals. `translate_preserving`
recases word-by-word, `plan_translations`/`detect_languages` walk a SceneTree.
`translatable_words()` / `rebuild_with()` are the split/reassemble pair the ONLINE
(Google) engine uses: an object name is not a sentence, so the raw name is never
sent — the words are, and the name is rebuilt around them (separators, digits,
codes and per-word casing preserved).
Gotcha: ambiguous tokens that look English (`AMBIGUOUS_DE`) are only translated
when the name carries independent language evidence (special chars or a
uniquely-single-language token).

### translations.py
Dictionaries + lookups (`to_english`, `to_german`, `lookup_en`,
`candidate_langs`, `add_translations`). Curated `DE_TO_EN` always wins over the
bundled bulk TSVs (`data/<lang>_en.tsv`). Parsed data is cached in a synthetic
module outside the `overseer` namespace so it survives per-request hot-reload,
keyed by file mtime/size. Gotcha: the German dictionary keys/values (e.g.
"Möbel" -> "furniture") are intentional data and must stay byte-for-byte.

## Conventions & gotchas
- Idempotency is a hard invariant: `normalize`/translate must be fixed points.
  Ambiguous bulk entries are excluded by default so `wand -> wall` does not
  drift to `bulwark` on the next pass.
- Producible casings (what a convention can emit): PascalCase, camelCase,
  lower_snake, UPPER_SNAKE, kebab. Detection additionally recognizes UPPER,
  LOWER, Capitalized, spaced, mixed and maps them to a producible target.
- Language heuristic: hard evidence = language-specific chars (umlauts etc.) or
  a token unique to one non-English language; English wins only when nothing
  else has evidence.
- translations.py German data (keys/values, umlauts included) is deliberate and
  non-ASCII by design — never "clean it up". Only code/comments stay ASCII.

Per-module prose: see the mirrored files under `docs/overseer/core/naming/`.
