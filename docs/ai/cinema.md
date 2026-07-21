# overseer.cinema — c4d host glue

The only package (besides `bridge/`) that imports `c4d`. It bridges the live
Cinema 4D document to the pure `overseer.core`/`naming` domain logic:
reading the scene into a `SceneTree`, and applying renames / reparents / layer
assignments / texture and tag / generator / simulation edits back onto the doc
with undo. Never imported by tests.

## Modules

### __init__.py
Empty package marker. `overseer.cinema.*` submodules are imported by string
(`importlib`) from `webapi` and are hot-reloaded per request.

### constants.py
`DOC_JOURNAL_ID` (BaseContainer id the change journal is stored under, travels
inside the .c4d) and `KNOWN_TYPES` (c4d type id -> readable label, incl. MoGraph
ids not exposed as `c4d.O*` symbols).

### adapter/ (package)
`SceneAdapter` — the doc<->`SceneTree` bridge and every scene mutation. One
file per domain class, composed as mixins in `scene.py`: `readers.py` (module
c4d readers), `materials.py` (`MaterialOps`), `previews.py` (`PreviewOps`),
`texpaths.py` (`TexturePathOps`), `texresize.py` (`TextureResizeOps`),
`layers.py` (`LayerOps`), `apply.py` (`ApplyOps`), `journal.py`
(`load_journal`/`save_journal`); `__init__.py` exports `SceneAdapter` + the
journal pair. `build_tree()` walks the object hierarchy once (geometry counts
via cache/deform-cache recursion) and records guid->object maps; all apply
methods (`apply_renames`/`apply_reparents`/`apply_layers`/`apply_bundle`/
`apply_plan`, material + texture + layer ops) wrap
`StartUndo`/`AddUndo`/`EndUndo` + `EventAdd`. Gotchas: material identity keys use `GetGUID()` not names (scenes carry
duplicate material names); `GetAllAssetsNew` RETURNS an int status and FILLS a
list arg (iterating the return value is the classic "int not iterable" crash);
path writes go to EVERY parameter holding the exact string (Octane/Redshift nodes
repeat a path across params) and are matched slash/case-insensitively; dunder
materials (`__octanetemp__`) are plugin-internal — skipped by the unused scan
and never deleted (`core.materials_logic`); `_host_resize` keeps bit depth end
to end (deep sources save with `SAVEBIT_32BITCHANNELS`, so hdr/exr stay float —
no tonemap) and refuses alpha maps rather than dropping the mask.

### webapi.py
The JSON API. Every op is a small `_op_*` handler in a registry: `_DOC_HANDLERS`
(`dirty`, `ui_settings_*` — `(payload, doc)`, skip the config load) and
`_CFG_HANDLERS` (`(req: ApiRequest)` with `op/payload/doc/cfg/data` +
`settings` property; plan/apply pairs share one handler and branch on `req.op`).
`handle(payload)` publishes an `_OP_LABELS` progress string and drops the scene
cache for `_MUTATING_OPS` afterward; `netinfo` is answered before any doc access.
`_get_scene()` caches `(adapter, tree)` on the `overseer` package keyed by the
doc dirty counter; selection is re-read on every hit (dirty ignores selection).
Material previews that come back EMPTY are negative-cached with the dirty
token they failed at — `GetPreview` can bump the doc's dirty counter, and
retrying failed previews on every fetch would feed the frontend watcher an
endless refresh loop.
Owns config/journal file IO and the PER-PROJECT analysis log
(`history/<project-slug>.json`, same slug as the UI settings; the flat
`analysis_history.json` is the pre-split log and is still read as a seed), Google-translate online engine
(stdlib urllib, persistent file cache — module globals do not survive hot-reload),
and the export mirror. Writes go to `DATA_DIR` (prefs dir when the plugin lives
under read-only Program Files). Audit ops (`tags_`/`gens_`/`files_`/`sims_`
prefixes) are delegated to the matching `audit_*` module.

### audit_tags.py
Tag audit (`tags_scan/add_phong/set_phong_angle/delete_duplicates/select`).
Skips `_INTERNAL_TAG_TYPES` plus every tag type registered without
`TAG_VISIBLE` (invisible data tags the artist can't see in the Object Manager
would dwarf the real tags). One row per OBJECT per type — an object's several
tags of a type land in that row's `tags` list. Point/polygon/edge selection
tags are folded into ONE "Selection" entry (`core.tags_logic.
merge_selection_types`): each tag carries its `kind`, the entry carries
`type_ids`, and `tags_select` accepts `type_ids` for it. Phong angles
read/written in radians via `c4d.utils`; symbol ids resolved through
`getattr(c4d, ...)` fallbacks so it survives across C4D versions.

### audit_generators.py
Generator parameter audit (`gens_scan/apply/select`). A declarative `_REGISTRY`
maps generator types (SDS, Cloner, Extrude, Instance, Symmetry) to params, each
with several candidate symbol names resolved to the first valid id. Dropdown
(`choice`) labels are read from the object's OWN description (exact Attribute
Manager strings), never hand-tabled. Deliberately does NOT diff on/off state
(a per-shot artistic choice, not a finding).

### audit_perf.py
Rebuild-cost audit (`perf_scan/select`) — which generator/deformer stalls the
viewport. Marks ONE object's cache dirty (`DIRTYFLAGS_CACHE`, no data change, no
undo step) and times `doc.ExecutePasses`; the fixed cost of an idle pass is
measured once and subtracted, the median of N runs counts. Ranking/verdict is
pure (`core/perf_logic.py`). Expensive by nature — the web UI only runs it on an
explicit click, never as a background scan.

### audit_sims.py
Simulation/cache audit (`sims_scan/select/set_enabled`). Tag/object type ids and
enable-parameter ids resolved via `getattr(c4d, ...)` with hardcoded numeric
fallbacks. Distinguishes sim kinds from cache kinds and flags whether a sim is
cached.

### audit_files.py
Non-image external file references (`files_scan/make_relative/select/pick_path/
relink`). Uses `GetAllAssetsNew` (with caches) plus explicit Alembic path params,
and drops the document's own file from the asset list. Rewrites paths across
every holder (all objects + all materials/shaders) and prefers project-relative
form.

### ui_settings.py
Per-project UI state persistence to `<data_dir>/configs/<slug>.json`; delegates
slug/sanitize to `core.ui_settings_logic`. Atomic temp-file write with a
direct-write fallback. Also owns the GLOBAL (all-projects) profile
`configs/_global.json` (`load_global_ui`/`save_global_ui`, ops
`ui_global_get`/`ui_global_set`): currently the web UI's area profile
(`hiddenAreas` — tabs hidden from the menu and excluded from the health
score). Slugs always start alphanumeric, so the underscore name cannot
collide.

## Conventions & gotchas

- Everything here runs on the C4D main thread (the ServerDialog timer drains the
  bridge queue) — direct doc access is only safe there. The HTTP server thread
  never touches the doc; it enqueues work and reads published progress state.
- Every scene mutation is ONE undo step: `doc.StartUndo()` / per-object
  `doc.AddUndo(UNDOTYPE_*, obj)` BEFORE the change / `doc.EndUndo()` / `EventAdd()`.
  New objects/tags use `UNDOTYPE_NEWOBJ`/`UNDOTYPE_NEW(TAG)`, deletes
  `UNDOTYPE_DELETE`, edits `UNDOTYPE_CHANGE`.
- `webapi` is re-imported on every API request (`reload_all()` purges all
  `overseer.*` except `bridge`), so module-level globals do NOT persist. Cross-
  request state must live either on the `overseer` package (scene/preview/icon
  caches — that package name is never purged) or in a file next to `config.json`
  (Google translate cache, journal, history).
- The scene cache is keyed on `doc.GetDirty(OBJECT|DATA)`, which bumps on real
  edits but NOT on selection/camera moves and NOT on plain renames — so mutating
  ops explicitly `invalidate_scene_cache()` and selection is recomputed on every
  cache hit. This keeps guids stable between a plan and its apply.
- Progress: each slow op publishes a human label from `_OP_LABELS` to the bridge
  (web UI polls `/api/progress`) and the C4D status bar; `handle()` always clears
  it in a `finally`, so a crashed op never leaves a stuck spinner.
- `GetAllAssetsNew(doc, allowDialogs, prefix, flags, outList)` returns an int
  status code and FILLS `outList` with dicts — never iterate the return value.
  It does NOT report every renderer's textures (C4D 2026 + Octane: none at
  all) — the texture scan therefore always merges a shader-tree walk on top.
- Plugin shaders (Octane ImageTexture id 1029508, file param 1100, …) keep
  their file params OUT of the description — `GetDescription` yields only the
  base-shader entries. Read/write texture paths via the raw `GetDataInstance()`
  container (matched by extension/value, not by hardcoded id).
- Material identity is `GetGUID()`, not name (duplicate names are common); path
  matching is normcase+normpath tolerant; path rewrites hit every parameter that
  holds the exact string.
- Writable-dir probing: a Program Files install is read-only for the unelevated
  C4D process, so all writes go to the per-user prefs dir (`DATA_DIR`), while the
  plugin dir stays the read-only source for the seed config.

Per-module prose: see the mirrored files under `docs/overseer/cinema/`.
