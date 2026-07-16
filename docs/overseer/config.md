# config.py

External configuration (`config.json`) → naming convention + keep lists. Pure module with NO side effects (easily testable): the caller reads the JSON file and calls `load_config(dict)`.

Schema v3: casing/language/number_pad/translations + per-section `keeps` map + the machine-local server settings. `migrate_config()` reads old configs forever; new configs are written v3 only.

- `CONFIG_SCHEMA_VERSION = 3`, `DEFAULT_CONFIG` — schema defaults (casing PascalCase, language en, number_pad 2, empty translations/keeps, plus the server settings `port` = `core/defaults.DEFAULT_PORT` and `listen_lan` = false).
- `MACHINE_LOCAL_KEYS` — config keys that describe THIS machine's server setup (`port`, `listen_lan`), not the naming standard.
- `_RETIRED_KEYS` — the removed rule-engine/preset era (`structure`, `rules`, `graph`, `preset`, `prefixes`, `groups`); `migrate_config()` silently drops them from old files.
- `Config` — dataclass bundling `convention`, `extra_translations`, and `keeps` (`kept(section)` accessor; `keep_names`/`accepted_unused` are pre-schema-3 aliases).
- `migrate_config(data)` — idempotent: drops retired keys, folds v2 flat `keep_names`/`accepted_unused` into the `keeps` map, stamps the schema. Unknown keys (port, listen_lan, …) are carried over untouched.
- `build_convention(data)` — builds a `NamingConvention` from casing/language/number_pad (language may be `None` = no translation).
- `load_config(data=None)` — merges over `DEFAULT_CONFIG`, migrates, returns a `Config`.
