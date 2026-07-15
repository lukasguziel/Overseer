# cinema/webapi.py

JSON API of the web frontend (c4d-dependent, runs on the C4D main thread). It is
freshly reloaded by `bridge.drain()` on every request (hot-reload), so it must
stay stateless at module level and use only the pure `overseer` logic plus the
`SceneAdapter`.

## Paths / constants

- `PLUGIN_DIR` — the .pyp directory (one above this package). `CONFIG_PATH`,
  `PRESETS_DIR`, `PLANS_DIR`, `HISTORY_PATH` derive from it.
- `EXPORT_PATH` / `EXPORT_CSV_PATH` — absolute repo paths where the full report /
  flat CSV land so Claude can read them directly.
- `PLANS_DIR` — restructuring plans learned/written by the skill.
- `_HISTORY_MAX` — max history entries kept.
- `_CSV_FIELDS` — columns of the flat one-object-per-row CSV.

## Helper functions

- `_write_export(report_dict)` — writes the JSON report to `EXPORT_PATH` (only if
  the parent dir exists); returns the path or None.
- `_write_csv(report_dict)` — writes a flat node table using `;` delimiter (German
  Excel locale) and a header row; returns (path, row count) or None.
- `_record_history(entry)` — appends an analysis entry (file/when/objects/...).
  Debounced: the same file within 60 s updates the last entry instead of spamming
  (live preview/refresh fire repeatedly). Capped to `_HISTORY_MAX`.
- `_read_history()` — reads the history list (best-effort).
- `_merge_layers(report_dict, layer_meta)` — combines the document's layer table
  (color/flags, incl. empty layers) with the analyzer's per-object counts
  (scope/visibility aware). Layers present in the scene but missing from metadata
  are appended so no assignment is lost.
- `_read_config_data()` — loads `config.json` as a raw dict (best-effort).
- `_preset_settings(data)` — extracts the settings payload from a preset: v2
  (`settings` key) or v1 (top-level minus `meta`).
- `_list_presets()` — all `presets/*.json` with meta + rule/group summary
  (migrated on the fly).
- `_slugify(name)` — filename-safe slug (falls back to "preset").
- `_save_preset(name, description, overwrite=False)` — snapshots the CURRENT
  config.json as a v2 preset file; strips the `preset` key (a snapshot is not
  derived from anything); refuses to clobber unless `overwrite`.
- `_delete_preset(preset_id)` — removes a preset file by id/name.
- `_load_preset(preset_id)` / `_load_plan(plan_id)` — load by id or file name
  (best-effort).
- `_list_plans()` — restructuring plans (`plans/*.json`) with short info.
- `_apply_preset(preset_id)` — writes the preset's settings snapshot VERBATIM to
  config.json. v2 presets carry a full snapshot incl. the node-editor graph, so
  manual graph layouts survive round trips; only a missing graph is regenerated.
  v1 preset files are migrated on the fly (and get a generated graph).
- `_load_cfg()` — loads config and registers `extra_translations`; returns
  (cfg, raw data).
- `_convention(settings, cfg)` — builds a `NamingConvention` from casing +
  numbering only. The naming pass NEVER translates — translation is a separate
  standalone tool (Translate tab) so renaming can no longer silently change an
  object's language.
- `_scope(settings, adapter)` — selected guids when `settings.selection`, else
  None.
- `_rule_dict(r)` — serializes a group rule.

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
  known, well-typed keys survive (`sanitize_ui`). Separate from presets: presets
  are named GLOBAL snapshots, these files are the silent per-project memory.
- `history` — reversed history list.
- `presets` / `apply_preset` / `save_preset` / `delete_preset` — preset CRUD.
- `plan_all` / `apply_all` — one-button combined plan (naming+structure+layers,
  one tree read). `apply_all` re-plans server-side on a fresh tree; guids sent by
  the client are trusted only as accept filters within the request, then applied
  via `apply_bundle` (one undo).
- `plans` / `apply_plan` — list plans; apply a deterministic plan (inline or by
  id) via `adapter.apply_plan`.
- `focus` — select + frame an object by guid.
- `delete_material` / `delete_unused_materials` / `fix_textures_relative` —
  material and texture-path maintenance.
- `detect` — detect the naming scheme from scene names.
- `rules` — active group rules, structure, declarative rules, prefixes,
  convention.
- `config` — read config (+ defaults) or, with `save`, write the posted data to
  config.json.
- `plan_naming` / `apply_naming` — plan/apply casing+numbering renames.
- `plan_structure` / `apply_structure` — plan/apply reparents honoring scope,
  safety filter, and tidy; reports skipped count.
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
