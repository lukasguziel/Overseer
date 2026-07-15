# config.py

External configuration (`config.json`) → convention/standard/rules. Pure module with NO side effects (easily testable): the caller reads the JSON file and calls `load_config(dict)`.

Schema v3: nested `structure` tree + versioned declarative `rules` list + per-section `keeps` map. `migrate_config()` reads v1/v2 configs forever; new configs are written v3 only.

- `CONFIG_SCHEMA_VERSION = 3`, `DEFAULT_CONFIG` — schema defaults (casing PascalCase, language en, number_pad 2, empty structure/rules/translations/keeps, plus the server settings `port` = `core/defaults.DEFAULT_PORT` and `listen_lan` = false).
- `MACHINE_LOCAL_KEYS` — config keys that describe THIS machine's server setup (`port`, `listen_lan`), not the naming/structure standard. webapi strips them from saved presets and preserves the current values when applying a preset, so presets stay portable and applying one never flips another machine's network exposure.
- `Config` — dataclass bundling `convention`, `standard`, `rules`, plus `prefixes` (legacy v1 view), `extra_translations`, and `keeps` (`kept(section)` accessor; `keep_names`/`accepted_unused` are pre-schema-3 aliases).
- `migrate_config(data)` — v1/v2 → v3, idempotent (v3 input returned normalized). Maps v1 `prefixes` `{"light": "LGT_"}` → prefix rules and flat `groups` → a flat `structure` tree; folds v2 flat `keep_names`/`accepted_unused` into the `keeps` map. Unknown keys (graph, preset, port, listen_lan, …) are carried over untouched.
- `build_convention(data)` — builds a `NamingConvention` from casing/language/number_pad (language may be `None` = no translation).
- `_collect_group_rules(nodes, parent, rules)` — recursively flattens the nested structure tree into `GroupRule`s, lowercasing keywords/aliases.
- `build_standard(data)` — nested `structure` → `StructureStandard`; empty → `default_standard()`.
- `structure_to_list(standard)` — inverse of `build_standard`: `StructureStandard` → nested tree. Rebuilds in path-depth order so parents exist before children.
- `_legacy_prefixes(ruleset)` — category→prefix view for v1 code paths; only enabled prefix rules matching exactly one category with no further conditions qualify (contextual rules cannot be flattened).
- `load_config(data=None)` — merges over `DEFAULT_CONFIG`, migrates, compiles rules, returns a `Config`.
