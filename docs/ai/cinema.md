# overseer.cinema — c4d host glue

The only package that imports `c4d`. It mirrors the `overseer.core` **area
layout 1:1** and bridges the live Cinema 4D document to the pure domain logic:
reading the scene into a `SceneTree`, and applying renames / reparents / layer
assignments / texture and tag / generator / simulation edits back onto the doc
with undo. Never imported by tests (a compile + area-mirror gate runs in
`tests/cinema/`).

## Modules (per area, same names as `core/` and `blender/`)

### __init__.py
Empty package marker. Submodules are hot-reloaded per request; the audit
modules are imported by string (`importlib`) from `context.audit()`.

### constants.py
`DOC_JOURNAL_ID` (BaseContainer id the change journal is stored under, travels
inside the .c4d) and `KNOWN_TYPES` (c4d type id -> readable label, incl. MoGraph
ids not exposed as `c4d.O*` symbols).

### scene/ (doc.py, readers.py, adapter.py)
`doc.py` — `CDoc`, the `SceneHost` wrapper over the active `c4d` document.
`readers.py` — module-level c4d readers (classify, type names, geometry
counts, layer names, save filters). `adapter.py` — `SceneAdapter`, the
doc<->`SceneTree` bridge, composed as mixins from the area modules below.
`build_tree()` walks the object hierarchy once (geometry counts via
cache/deform-cache recursion) and records guid->object maps; all apply methods
wrap `StartUndo`/`AddUndo`/`EndUndo` + `EventAdd`.

### organize/ (apply.py, journal.py)
`apply.py` — `ApplyOps`: `apply_renames`/`apply_reparents`/`apply_layers`/
`revert`, records `last_changes` for the journal. `journal.py` —
`load_journal`/`save_journal` (journal travels in the doc's BaseContainer,
file fallback).

### layers.py
`LayerOps`: `scan_layers`, delete/color ops for C4D layer objects.

### materials.py
`MaterialOps`: material scan/focus/delete. Identity keys use `GetGUID()` not
names (scenes carry duplicate material names); dunder materials
(`__octanetemp__`) are plugin-internal — skipped by the unused scan and never
deleted (`core.materials.logic`).

### textures/ (paths.py, resize.py, previews.py)
`paths.py` — `TexturePathOps`: texture scan, relink, repath, collect. Path
writes go to EVERY parameter holding the exact string (Octane/Redshift nodes
repeat a path across params), matched slash/case-insensitively. Plugin
shaders keep file params OUT of the description — read/write via the raw
`GetDataInstance()` container. `resize.py` — `TextureResizeOps`:
`_host_resize` keeps bit depth end to end (deep sources save with
`SAVEBIT_32BITCHANNELS`, so hdr/exr stay float — no tonemap) and refuses
alpha maps rather than dropping the mask. `previews.py` — `PreviewOps`
(material/texture preview data-URIs).

### tags.py
`CinemaTagsAudit` (subclass of `core.tags.audit.TagsAudit`, exposes `AUDIT`).
Skips `_INTERNAL_TAG_TYPES` plus every tag type registered without
`TAG_VISIBLE`. One row per OBJECT per type. Point/polygon/edge selection tags
are folded into ONE "Selection" entry (`core.tags.logic.merge_selection_types`).
Phong angles read/written in radians via `c4d.utils`; symbol ids resolved
through `getattr(c4d, ...)` fallbacks so it survives across C4D versions.

### generators.py
Generator parameter audit. A declarative `_REGISTRY` maps generator types
(SDS, Cloner, Extrude, Instance, Symmetry) to params, each with several
candidate symbol names resolved to the first valid id. Dropdown (`choice`)
labels are read from the object's OWN description, never hand-tabled.
Deliberately does NOT diff on/off state.

### perf.py
Rebuild-cost audit — which generator/deformer stalls the viewport. Marks ONE
object's cache dirty (`DIRTYFLAGS_CACHE`, no data change, no undo step) and
times `doc.ExecutePasses`; idle-pass cost is subtracted, the median of N runs
counts. Ranking/verdict is pure (`core/perf/logic.py`). Only runs on an
explicit click.

### sims.py
Simulation/cache audit. Tag/object type ids and enable-parameter ids resolved
via `getattr(c4d, ...)` with hardcoded numeric fallbacks. Distinguishes sim
kinds from cache kinds and flags whether a sim is cached.

### files.py
Non-image external file references. Uses `GetAllAssetsNew` (with caches) plus
explicit Alembic path params, drops the document's own file, rewrites paths
across every holder and prefers project-relative form.

### context.py / webapi.py
`context.py` — `CinemaContext(HostContext)`: the only c4d-specific surface the
shared op layer needs (active doc, adapter factory, paths/export mirror,
progress -> bridge + C4D status bar, native pickers, type icons, per-area
`audit(prefix)` lookup). `webapi.py` — thin: binds
`core.hostapi.webapi.WebApi` to a `CinemaContext` and exposes `handle`.
All `_op_*` handlers, caches and file IO live in the SHARED
`core/hostapi/webapi.py` (see [hostapi.md](hostapi.md)).

### bridge/
HTTP server (BG thread) + main-thread queue + progress + ServerDialog. The
process singleton — excluded from hot-reload; changes here need a C4D restart.

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
- Material identity is `GetGUID()`, not name (duplicate names are common); path
  matching is normcase+normpath tolerant; path rewrites hit every parameter that
  holds the exact string.
- Writable-dir probing: a Program Files install is read-only for the unelevated
  C4D process, so all writes go to the per-user prefs dir (`DATA_DIR`), while the
  plugin dir stays the read-only source for the seed config.

Per-module prose: see the mirrored files under `docs/overseer/cinema/`.
