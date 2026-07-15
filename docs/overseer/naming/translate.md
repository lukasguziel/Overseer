# translate

Translation tool: detects the language of object names and proposes a casing-preserving translation into the target language (pure, no `c4d`).

Unlike `NamingConvention`, casing is NOT unified: each word is replaced in place while the original upper/lowercase pattern, separators, and trailing numbers are preserved, letting the user decide per object.

**False-positive guard:** several German dictionary keys are also ordinary English words (`bad`, `wand`, `regal`, ...). Translating them blindly would turn `bad_geometry` into `bathroom_geometry`. Such ambiguous words are translated (DE->EN) only when the surrounding name carries other German evidence (an umlaut or an unambiguous German word).

## `AMBIGUOUS_DE`
Literal set of German keys that collide with common English words. Kept literal and intersected with the live dictionary at call time so runtime-added translations never accidentally join it.

## `TranslateProposal` (dataclass)
Linked to its `node: SceneNode` (`guid` and `old` are read-through properties of the node), plus `new`, `words` (list of `(source, translated)` pairs actually replaced), and detected `lang` of `old`. The apply path builds a `RenameOp(node=proposal.node, ...)` straight from the proposal.

## `_match_case(src, tgt)`
Transfers the casing pattern from `src` onto the translated word `tgt` (upper / lower / capitalized / verbatim).

## `detect_name_language(name)`
Detected source language of a single name (`de` / `en` / `unknown`).

## `_has_german_evidence(name)`
`True` when the name clearly contains German beyond ambiguous words (umlaut, or an unambiguous German dictionary word).

## `translate_preserving(name, target='en')`
Translates words in the name into `target`, preserving casing/structure. `target='en'`: German -> English, ambiguity-guarded. `target='de'`: English -> German (unguarded). Returns `(new_name, [(source, translated), ...])`; the list is empty when nothing was translatable.

## `plan_translations(tree, scope=None, target='en')`
Walks the tree (optionally filtered by a set of guids) and returns `TranslateProposal`s for every object whose name actually changes.

## `LanguageSummary` (dataclass)
Counts `de` / `en` / `unknown` / `total` and the `dominant` language; `to_dict()` serializes it.

## `detect_languages(tree, scope=None)`
Aggregates detected language over all (scoped) object names into a `LanguageSummary`; dominant requires a strict majority, else `unknown`.

## `translatable_words(name)`
The words inside an object name, lowercased, in order. Object names are not sentences: `body_rear_wing_part_usm.1` is five words glued together with separators plus a code and an index. A translator fed the raw name recognizes nothing — fed the WORDS it recognizes almost all of them. Words shorter than `MIN_WORD` (2) are left alone: a lone `a` or `x` is an index or an axis, never a word worth translating.

## `rebuild_with(name, mapping)`
Puts translated words back into the name, keeping everything else. Separators, digits, codes and the casing of each word survive — only the words the `mapping` knows are swapped, so `Body_Rear_Wing.1` stays `<Word>_<Word>_<Word>.1` in the target language. Returns `(new_name, [(source, translated), ...])`.
