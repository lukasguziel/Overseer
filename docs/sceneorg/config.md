# config.py

External configuration (`config.json`) → convention/standard/rules. Pure module with NO side effects (easily testable): the dialog reads the JSON file and calls `load_config(dict)`.

Schema v2: nested `structure` tree + versioned declarative `rules` list. `migrate_config()` reads v1 configs forever; new configs are written v2 only.

- `CONFIG_SCHEMA_VERSION = 2`, `DEFAULT_CONFIG` — schema defaults (casing PascalCase, language en, number_pad 2, empty structure/rules/translations).
- `Config` — dataclass bundling `convention`, `standard`, `rules`, plus `prefixes` (legacy v1 view) and `extra_translations`.
- `migrate_config(data)` — v1 → v2, idempotent (v2 input returned normalized). Maps `prefixes` `{"light": "LGT_"}` → prefix rules and flat `groups` → a flat `structure` tree. Unknown keys (graph, preset, …) are carried over untouched.
- `build_convention(data)` — builds a `NamingConvention` from casing/language/number_pad (language may be `None` = no translation).
- `_collect_group_rules(nodes, parent, rules)` — recursively flattens the nested structure tree into `GroupRule`s, lowercasing keywords/aliases.
- `build_standard(data)` — nested `structure` → `StructureStandard`; empty → `default_standard()`.
- `structure_to_list(standard)` — inverse of `build_standard`: `StructureStandard` → nested tree. Rebuilds in path-depth order so parents exist before children.
- `_legacy_prefixes(ruleset)` — category→prefix view for v1 code paths; only enabled prefix rules matching exactly one category with no further conditions qualify (contextual rules cannot be flattened).
- `load_config(data=None)` — merges over `DEFAULT_CONFIG`, migrates, compiles rules, returns a `Config`.
