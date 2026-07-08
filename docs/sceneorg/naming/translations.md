# translations

DE<->EN dictionary for interior/ArchViz terms (pure, data-driven).

## `DE_TO_EN`
Canonical German -> English mapping. Umlaut forms are provided additionally as ae/oe/ue variants so both spellings resolve.

## `EN_TO_DE`
Reverse map built from `DE_TO_EN`; the first canonical reverse match wins (`setdefault`).

## `DE_WORDS` / `EN_WORDS`
Full word sets used for language detection. `EN_WORDS` extends the English values with extra plural/synonym forms (`lights`, `chairs`, `props`, `cam`, ...).

## `to_english(token)` / `to_german(token)`
Look up a single lowercase token; return it unchanged if not in the dictionary.

## `add_translations(extra)`
Extends the dictionary at runtime with additional de->en pairs. Mutates the module globals (`DE_TO_EN`, `EN_TO_DE`, `DE_WORDS`, `EN_WORDS`); lowercases inputs. Intended for the one-time config load — hot-reload re-imports the module fresh, so no accumulation across reloads.
