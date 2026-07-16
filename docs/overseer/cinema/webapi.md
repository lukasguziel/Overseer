# cinema/webapi.py

JSON API of the web frontend (c4d-dependent, runs on the C4D main thread). It is
freshly reloaded by `bridge.drain()` on every request (hot-reload), so it must
stay stateless at module level and use only the pure `overseer` logic plus the
`SceneAdapter`.

## Dispatch structure

Every op is a small `_op_*` handler function looked up in a registry — no
if-ladder. Three tiers, dispatched by `_handle(payload)` in this order:

1. `netinfo` — answered before any document access.
2. `_DOC_HANDLERS` (`dirty`, `ui_settings_get/set`) — signature
   `(payload, doc)`; cheap per-poll ops that deliberately skip the config load.
3. `_CFG_HANDLERS` — signature `(req: ApiRequest)`; `ApiRequest` bundles
   `op`/`payload`/`doc`/`cfg`/`data` (raw config dict) and exposes
   `settings` as a property. Plan/apply pairs share one handler and branch on
   `req.op` (e.g. `_op_plan_naming` serves `plan_naming` + `apply_naming`);
   `set_keeps`/`set_keep_names`/`set_accepted_unused` alias onto `_op_set_keeps`.
4. Fallback: ops whose prefix is in `_AUDIT_MODULES` are forwarded to the
   matching `audit_*` module's `handle()`; anything else is an error dict.

`handle(payload)` wraps `_handle` with the `_OP_LABELS` progress label and, for
`_MUTATING_OPS`, invalidates the scene cache in a `finally`.

## Paths / constants

All module constants live in one block at the top.

- `PLUGIN_DIR` — the .pyp directory (one above this package). `DATA_DIR` is the
  plugin dir when writable, else the per-user prefs dir `overseer/` (a legacy
  `scene_organizer/` prefs dir from the Scene Organizer days is renamed on first
  use — one-time migration that keeps config, presets, history and caches; if
  the rename fails because the dir is locked, the old dir keeps being used —
  losing the user's settings would be worse than the old folder name). When
  `DATA_DIR` is the prefs dir, a `config.json` shipped next to the .pyp seeds it
  once. `CONFIG_PATH`, `PRESETS_DIR`, `HISTORY_DIR`, `CHANGES_PATH`,
  `GOOGLE_CACHE_PATH` derive from `DATA_DIR`; `SHIPPED_PRESETS_DIR` and
  `PLANS_DIR` from `PLUGIN_DIR`.
- `EXPORT_PATH` / `EXPORT_CSV_PATH` — where the full report / flat CSV land so
  Claude can read them directly: `OVERSEER_EXPORT_DIR` env override, else the
  dev repo's `var/` (via the deploy-stamped `dev_repo.txt`, so exports never
  clutter the repo root), else `DATA_DIR`.
- `PLANS_DIR` — restructuring plans learned/written by the skill.
- `_HISTORY_MAX` / `_CHANGES_MAX` / `_GCACHE_MAX` — caps for analysis history,
  change journal, and the Google translation cache (the gcache drops its older
  half when the cap is exceeded).
- `_CSV_FIELDS` — columns of the flat one-object-per-row CSV.

## Helper functions

- `_write_export(report_dict)` — writes the JSON report to `EXPORT_PATH` (only if
  the parent dir exists); returns the path or None.
- `_write_csv(report_dict)` — writes a flat node table using `;` delimiter (German
  Excel locale) and a header row; returns (path, row count) or None.
- `_history_path(doc)` — per-project log file `history/<slug>.json`; same
  project slug the UI settings use, so one project's runs never crowd out
  another's (the log is capped per project).
- `_record_history(doc, entry)` — appends an analysis entry (file/when/objects/...).
  Debounced: the same file within 60 s updates the last entry instead of spamming
  (live preview/refresh fire repeatedly). Capped to `_HISTORY_MAX`.
- `_read_history(doc)` — reads the per-project history (best-effort). With no
  per-project log yet it seeds from `_legacy_history` — the pre-split global
  `analysis_history.json`, kept as an archive, filtered to this document.
  `clear_history` therefore writes an empty log instead of deleting the file —
  an absent file would fall back to the global log and resurrect the runs.
- `_merge_layers(report_dict, layer_meta)` — combines the document's layer table
  (color/flags, incl. empty layers) with the analyzer's per-object counts
  (scope/visibility aware). Layers present in the scene but missing from metadata
  are appended so no assignment is lost.
- `_read_config_data()` — loads `config.json` as a raw dict (best-effort).
- `_load_cfg()` — loads config and registers `extra_translations`; returns
  (cfg, raw data).
- `_convention(settings, cfg)` — builds a `NamingConvention` from casing +
  numbering only. The naming pass NEVER translates — translation is a separate
  standalone tool (Translate tab) so renaming can no longer silently change an
  object's language.
- `_scope(settings, adapter)` — selected guids when `settings.selection`, else
  None.
- `_rule_dict(r)` — serializes a group rule.
- `_lan_ip()` — the machine's LAN address: a connectionless UDP "connect" just
  picks the outbound interface, nothing is sent.
- `_netinfo(payload)` — LAN state for the open-on-phone QR flow. POST
  `{"listen_lan": bool}` persists the opt-in; the bind itself only changes on a
  C4D restart. Reports the running server's port via `bridge.server_port()`.
  All bridge lookups go through `getattr` hedges: bridge is the
  never-hot-reloaded singleton, so right after a deploy the RUNNING bridge may
  predate newer attributes until a C4D restart.
- `_google_plan(tree, scope, target)` — online translation planning. It
  translates WORDS, not raw names: "body_rear_wing_part_usm.1" means nothing to
  a translator, while "body", "rear", "wing", "part" are trivial — and words
  repeat across a scene, so the `google_cache.json` hit rate is far higher than
  per-name. Batches of 40 words per request; a name's source language is what
  most of its words came from.

## handle(payload)

Single entry point dispatching on `payload["op"]` against the active document
(errors if none). Ops:

- `analyze` / `export` / `export_csv` — reads the tree with a progress callback
  that reports to the `bridge` singleton (polled by the web UI via
  `/api/progress`) and mirrors into the C4D status bar. Analyze narrows all stats
  by selection scope and excludes hidden objects by default; exports always cover
  the whole scene (the Claude channel) and always include hidden. Adds file size,
  materials, textures, and merged layers, records history (non-scoped only), and
  writes the export. `export_csv` additionally writes the flat CSV. `bridge`
  progress and status bar are always cleared in a `finally`.
- `ui_settings_get` / `ui_settings_set` — per-project UI settings persistence
  (cheap ops, no config load). `get` returns `{found, ui}` with the stored
  clickable settings for the ACTIVE document; `set` persists the posted `ui`
  blob for it. Backed by `cinema/ui_settings.py`, one JSON per project under
  `DATA_DIR/configs/<slug>.json` (slug = `core/ui_settings_logic.project_slug`
  of the doc path + name; unsaved docs with neither are skipped). Only the
  known, well-typed keys survive (`sanitize_ui`) — the silent per-project
  memory.
- `history` — reversed history list.
- `focus` — select + frame an object by guid.
- `delete_material` / `delete_unused_materials` / `fix_textures_relative` —
  material and texture-path maintenance.
- `detect` — detect the naming scheme from scene names.
- `config` — read config (+ defaults) or, with `save`, write the posted data to
  config.json.
- `plan_naming` / `apply_naming` — plan/apply casing+numbering renames. The web
  UI's eye toggle maps to `settings.include_hidden`: when false, hidden objects
  leave the rename worklist (they keep their names and still block
  numbers/dedupe as siblings). Defaults to true so API callers without the flag
  keep planning everything.
- `plan_translate` / `apply_translate` — standalone translation with its own
  target language (independent of the naming convention). Apply only renames the
  user-accepted guids.
- `plan_layers` / `apply_layers` — plan/apply type-axis layer assignment with a
  by-layer count.
- `plan_layer_suggestions` — `{diff:[{guid,name,layer}], count}`: for objects
  with no layer, the nearest ancestor's layer (inherit-down). Pure planner, keeps
  filtered; the no-layer worklist offers these as one-click assigns.
- `layer_mismatches` — `{findings:[{guid,name,path,parent,parent_layer,child_layer}], count}`:
  objects on a different layer than their parent. Informational only (never
  auto-applied); accept-as-is goes through `set_keeps` section `layers`.
- `delete_layer` `{name}` / `delete_empty_layers` — delete layers that nothing
  references (objects/materials/tags), one undo step. Returns `{deleted}`.
  `delete_layer` refuses a non-empty layer (returns `deleted:0`).
- `assign_layer` / `move_to_group` — direct batch actions from the asset
  browser: `{guids, layer}` assigns the picked objects to a named layer
  (created if missing), `{guids, group}` reparents them under a named null
  (`ensure_group_path`, created at root if missing). The user chose both the
  objects and the target explicitly, so no plan or safety filter runs; both are
  one undo step and recorded in the change history.
- `changes` — the scene's change journal newest-first. Every apply op records
  one run entry (`_record_change`) `{id, ts, at, kind, summary, items,
  revertible, reverted}`, `items` copied from `adapter.last_changes` (each op
  also carries a per-op `reverted` flag). The journal is **persisted with the
  scene** (M2): `adapter.load_journal`/`save_journal` store it in the document's
  BaseContainer + a sidecar next to the .c4d, falling back to the machine-local
  `change_history.json` (max 200) for unsaved scenes. Material deletes / texture
  fixes are logged summary-only (`revertible=false`).
- `revert_change` `{id, items?}` — rebuilds the tree and calls `adapter.revert`
  on the run's ops. `items` (op indices) = **per-op selective revert**; omitted
  = **full-run revert**. Already-reverted ops are filtered
  (`journal.items_to_revert`); only ops that actually reverted are flagged
  (`journal.mark_reverted`), so missing targets stay actionable. Returns
  `{reverted, missing, results}`. `clear_changes` empties the journal (does not
  touch the scene).
- unknown op → error dict.

## Texture ops (M4)

- `texture_repath` `{paths, mode:'relative'|'absolute', material?}` — batch
  relative/absolute path conversion; journals as `textures_repath`.
- `texture_resize` `{paths, percent:25|50|75}` — batch resize to copies +
  relink; journals as `textures_resize`. Returns `{resized, skipped, relinked,
  results:[{file,status,note,to}]}`; a bad percent returns `{ok:false,error}`.
- Both are in `_MUTATING_OPS` (drop the scene cache) and carry `_OP_LABELS`
  progress strings.
