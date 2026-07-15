# overseer â€” package root

Core principle: pure domain logic is strictly separated from `c4d`. Everything
here except `bridge.py` is importable in CI without Cinema 4D.

## Package-level modules

### __init__.py
Holds `__version__` only. Keep it import-light â€” pulling in heavy submodules here
would break the `c4d`-free test import.

### bridge.py
[c4d] The HTTP server (background thread) + main-thread request queue + progress
state. PROCESS SINGLETON: it is deliberately excluded from `reload_all()` (via
`_RELOAD_KEEP`) so the server, queue and progress survive hot-reloads. `drain()`
runs on the ServerDialog timer, purges every `overseer.*` submodule except this
one, then dispatches to `cinema.webapi.handle`. A `reload` op also clears the
cross-request scene cache on the `overseer` package. Changing `bridge.py` itself
requires a full C4D restart.

### config.py
Pure. `config.json` schema 3; `migrate_config()` reads v1/v2/v3 forever (v1
`prefixes`/`groups` -> rules/structure; v2 flat keep lists -> per-section `keeps`
map). `load_config()` merges over `DEFAULT_CONFIG`, compiles the rule set, and
builds the `NamingConvention` + `StructureStandard`. `Config.keep_names` /
`accepted_unused` are aliases for pre-schema-3 call sites.

## Subpackages
- core/ â€” pure domain logic (see [core.md](core.md))
- cinema/ â€” c4d host glue (see [cinema.md](cinema.md))
- naming/ â€” naming convention pipeline (see [naming.md](naming.md))
- structure/ â€” group standard + rule engine (see [structure.md](structure.md))

## Conventions & gotchas
- Only `cinema/` and `bridge.py` import `c4d`; nothing else may, so tests import
  the rest without Cinema 4D.
- `bridge` is the process singleton â€” never hot-reload-purged; `reload_all()`
  drops every other `overseer.*` module so the next request re-imports fresh
  source (no restart, no re-click for logic/webapi edits).

Per-module prose: see the mirrored files under `docs/overseer/`.
