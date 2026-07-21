# overseer.blender — Blender host glue (port of `cinema/`)

This package is the Blender-side twin of `overseer/cinema/`. It imports `bpy`
(never imported by CI tests, exactly like `cinema/` never imports `c4d` in
tests). Everything under `core/`, `naming/`, `config.py` and the whole
`frontend/` web UI are **shared verbatim** with the Cinema 4D build — the port
only re-implements the host glue (`cinema/`) and the loader/bridge.

**Goal:** the *same* web frontend, unchanged, talks to a Blender backend that
answers the identical JSON `/api` contract. Where Blender models a concept
differently (or better) than C4D, we map to the Blender-native primitive and
keep the same API shape so the UI needs no changes.

## The golden rule

The frontend is frozen. Every `/api/<op>` handler MUST return the **same JSON
shape** as `cinema/webapi.py` returns for that op. When in doubt, open the
matching `_op_*` in `cinema/webapi.py` and mirror its result dict key-for-key.
Read `docs/api.md` for the op table.

## C4D → Blender concept mapping

| C4D concept | Blender primitive | Notes |
|---|---|---|
| active document (`GetActiveDocument`) | `bpy.context.scene` + `bpy.data` + the `.blend` | wrapped by `blender/scene.py::BScene` |
| object hierarchy (`GetDown`/`GetNext`) | `bpy.data.objects` via `.parent`/`.children_recursive` | roots = objects with no parent, in a stable order |
| object identity / guid | sequential int assigned during `build_tree` (same as C4D) | a live `bpy.types.Object` is mapped in `_by_guid` |
| stable id (`GetGUID`) | `object.session_uid` (int, stable within a session) | used for `_by_sid` |
| categories | LIGHT→light, CAMERA→camera, EMPTY→null, MESH→mesh, CURVE→spline, other | see `blender/adapter/readers.py::classify` |
| point/poly count | evaluated mesh via depsgraph (`obj.evaluated_get(depsgraph).to_mesh()`) | mirrors C4D's cache/deform-cache recursion; counts the *rendered* result of modifiers/geonodes |
| editor visibility | `obj.visible_get()` / `hide_viewport` | `visible=False` when hidden |
| **layers** | **collections** (`bpy.data.collections`) | C4D layer name ⇒ collection of that name. An object's "layer" = its owning non-scene collection (first, if several). Assigning a layer = linking into that collection (and unlinking from prior overseer-managed ones). |
| layer color | collection `color_tag` (`'COLOR_01'`..`'COLOR_08'`, or `'NONE'`) | Blender has only 8 preset tags; map an RGB triple to the nearest preset. Keep the API `[r,g,b]` shape; store nearest tag. |
| layer solo/view/render/locked | `collection.hide_viewport`/`hide_render`; `LayerCollection.exclude`; no per-collection lock | fill what exists, default the rest. |
| materials | `bpy.data.materials` (node-based) | identity key = `material.name_full` (or `session_uid`); duplicate base names exist (`.001`) just like C4D dup names. |
| unused material | `material.users == 0` **or** assigned to no object's material slots | `__`-prefixed / internal names are skipped (see `core.materials_logic`). |
| textures | `bpy.data.images` + Image Texture nodes | path = `image.filepath` (raw) / `filepath_from_user()`; `//` prefix means blend-relative. |
| relative/absolute path | `//` prefix (blend-relative) | use `bpy.path.abspath` / `bpy.path.relpath`; "make relative" = rewrite to `//…`. |
| **tags** (C4D) | **modifiers + constraints + custom properties + vertex groups/UV maps** | Blender has no "tags". The Tags tab audits *object attachments*: one row per (object, attachment-kind). Phong/smoothing ⇒ Auto-Smooth / "Shade Smooth" (a mesh property, not a tag). Duplicate-material-tag ⇒ duplicate material slots referencing the same material. |
| **generators** (SDS/Cloner/Extrude/Instance/Symmetry) | **modifiers** (Subdivision Surface, Array, Screw, Solidify, Mirror) + Geometry Nodes; instancing (`instance_type`) | declarative `_REGISTRY` maps a modifier type to its exposed params, read from `modifier.bl_rna` (never hand-tabled labels). |
| **sims/caches** | **physics**: Cloth, Soft Body, Rigid Body, Fluid (Mantaflow), Dynamic Paint; particle systems; point caches | distinguish sim kinds from cache kinds; flag whether baked (`point_cache.is_baked`). |
| perf / viewport cost | depsgraph re-evaluation timing | tag one object for update (`obj.update_tag()`), time `depsgraph.update()`; subtract idle-pass cost; median of N. |
| files (external refs) | linked libraries (`bpy.data.libraries`), images, caches, fonts, sounds, `.abc`/`.usd` cache modifiers | drop the `.blend`'s own path; prefer blend-relative. |
| undo step | `bpy.ops.ed.undo_push(message=...)` AFTER a batch of edits | Blender groups by push, not Start/AddUndo/End. Do all edits, then ONE `undo_push`. No per-object AddUndo. |
| `EventAdd()` | `obj.update_tag()` + view-layer update; usually implicit | tag changed data so the UI/viewport refresh. |
| focus/frame object | select + `view3d.view_selected` via a temp context override | see `adapter/scene.py::focus`. |
| status bar | `bpy.context.workspace.status_text_set` (best-effort) | progress still primarily flows to the web UI via `set_progress`. |
| file/folder picker | a modal `bpy.types.Operator` invoking `fileselect_add` | runs on the main thread from the pump; returns the chosen path to the waiting request. If not feasible in a headless/timer context, return `{"cancelled": True}` gracefully — the UI already handles that. |

## Main-thread model

Blender's `bpy.data` is only safe to touch on the main thread. Mirror the C4D
design:

- HTTP server runs on a **background thread** (`blender/server.py`,
  host-neutral copy of `bridge/server.py` with no `bpy`). It only enqueues
  work and reads published progress — never touches `bpy`.
- A **main-thread pump** drains the queue. In C4D the `ServerDialog.Timer`
  drains it; in Blender a `bpy.app.timers` callback does
  (`blender/pump.py`). The timer runs on the main thread, so the dispatched
  `webapi.handle` can touch `bpy` safely.
- Per-request **hot reload**: `blender/reload.py::reload_all()` purges every
  `overseer.*` module EXCEPT the process-singleton host
  (`overseer.blender.host` + `overseer.blender.pump` + `overseer.blender.server`
  + `overseer.blender.reload`). So editing `blender/webapi.py`, any adapter or
  any audit takes effect on the next request with no Blender restart — same DX
  as the C4D build.

## The `BScene` "doc" wrapper (`blender/scene.py`)

`cinema/webapi.py` threads a live `c4d` `doc` through every handler. To reuse
that structure, `blender/webapi.py` threads a `BScene` object that exposes the
handful of doc-methods the handlers call, mapped onto `bpy`:

| C4D `doc` call | `BScene` method | Blender impl |
|---|---|---|
| `GetActiveDocument()` | `BScene.active()` | wraps `bpy.context.scene` / `bpy.data` |
| `GetDocumentName()` | `.name` | `basename(bpy.data.filepath)` or `"(unsaved)"` |
| `GetDocumentPath()` | `.path` | `dirname(bpy.data.filepath)` |
| `GetDirty(OBJECT\|DATA)` | `.dirty()` | sum of `bpy.data.objects`/scene depsgraph update counters, or a monotonic edit token (see impl) |
| active selection | `.selection()` | `bpy.context.selected_objects` (+ order) |
| undo push | `.undo_push(msg)` | `bpy.ops.ed.undo_push(message=msg)` |

`BScene.dirty()` must bump on real edits but stay stable across selection /
camera moves (the scene cache is keyed on it — see below).

**Timer-context gotcha:** every request runs inside the `bpy.app.timers` pump,
where `bpy.context` has NO screen context — `bpy.context.selected_objects` /
`active_object` simply do not exist there. Any selection read must go through
`BScene.object_selected(obj)` / `BScene.selected_objects()`, which call
`obj.select_get(view_layer=...)` with an explicit view layer
(`BScene.view_layer()`: context view layer, else `scene.view_layers[0]`).
A bare `obj.select_get()` or `bpy.context.selected_objects` works in the
Python console but silently returns nothing via the web API — that bug shipped
once (the Selection scope never updated in Blender).

## SceneAdapter contract (`blender/adapter/`)

`SceneAdapter` is composed from mixins exactly like C4D's. It is constructed
`SceneAdapter(scene: BScene)` and MUST provide these members (called by
`blender/webapi.py`; keep names identical to the C4D adapter):

**Core (adapter/scene.py — provided by the foundation):**
- `doc` attribute (the `BScene`), `_by_guid: dict[int, bpy.types.Object]`,
  `_by_sid`, `_selected_direct: set[int]`, `_selected_subtree: set[int]`,
  `last_changes: list[dict]`
- `build_tree(progress=None) -> core.model.SceneTree` — walks the object
  hierarchy once, assigns sequential guids, fills every `SceneNode` field
  (name, type_name, category, guid, depth, point_count, poly_count, visible,
  layer). Records `_by_guid`/`_by_sid` and selection sets.
- `selected_guids(include_children=True) -> set[int]`
- `focus(guid) -> bool` — select + frame in the viewport.

**Apply (adapter/apply.py — ApplyOps):**
- `rename_object(guid, new_name) -> bool` (sets `last_changes`)
- `apply_renames(list[ops.RenameOp]) -> int`
- `apply_reparents(list[ops.ReparentOp]) -> int` (reparent under a named Empty)
- `apply_layers(list[ops.LayerOp]) -> int` (link into a named collection)
- `revert(items: list[dict]) -> {"reverted": int, "missing": int, "results": [...]}`
  Each `last_changes` item is a dict the journal stores and `revert` consumes;
  keep the SAME item schema the C4D `apply.py`/`journal.py` use so
  `core/journal.py` (shared) works unchanged.

**Collections=Layers (adapter/collections.py — LayerOps):**
- `scan_layers() -> list[dict]` (name, color[r,g,b]|None, solo, view, render,
  locked, materials, tags)
- `_layer_object_counts() -> dict[str,int]`
- `delete_layer(name) -> int`, `delete_empty_layers(keep:set) -> int`
- `set_layer_colors(colors: dict[str,[r,g,b]]) -> int`

**Materials (adapter/materials.py — MaterialOps):**
- `scan_materials(include_hidden, accepted) -> dict` (shape per C4D)
- `focus_material(name) -> dict`, `delete_material(name, include_hidden) -> int`,
  `delete_unused_materials(include_hidden, accepted) -> int`

**Previews (adapter/previews.py — PreviewOps):**
- `material_previews(names, size, progress) -> dict[name, dataURI]`
- `texture_previews(paths, size, progress) -> dict[path, dataURI]`
  (use `bpy.data.images[...].preview` / render, or Pillow from `vendor/`; a
  transparent 1×1 PNG data-URI is an acceptable fallback if unavailable.)

**Texture paths (adapter/texpaths.py — TexturePathOps):**
- `scan_textures(include_hidden, accepted) -> dict`
- `make_textures_relative(materials) -> dict`
- `texture_owners(path) -> dict`, `collect_textures(materials, subdir, paths) -> dict`
- `relink_textures(folder, progress) -> dict`, `clear_missing_textures(accepted) -> dict`
- `set_texture_path(path, new_path, material) -> dict`
- `texture_repath(paths, mode, material) -> dict`

**Texture resize (adapter/texresize.py — TextureResizeOps):**
- `texture_resize(paths, percent) -> dict` (Pillow from `vendor/`, keep bit depth)

Return-dict keys for each are defined by the matching C4D method — mirror them.

## Audit modules

`blender/audit_{tags,generators,sims,files,perf}.py`. Each exposes:

```python
def handle(op, payload, doc, adapter, tree, progress) -> dict: ...
```

and `audit_generators`/`audit_sims` also expose `has_any(adapter, tree) -> bool`
(used by `_op_analyze` to show/hide the tab). Ops are `<prefix>_<verb>`
(`tags_scan`, `gens_apply`, `sims_set_enabled`, `files_relink`, `perf_scan`,
…). Mirror the C4D audit result shapes (open the matching `cinema/audit_*.py`).

Blender specifics:
- **tags**: audit modifiers + constraints (+ optionally custom props). One row
  per (object, kind). `tags_add_phong`→ set Auto-Smooth / shade-smooth;
  `tags_delete_duplicates`→ collapse duplicate material slots.
- **generators**: modifiers via `bl_rna` param introspection; instancing.
- **sims**: physics modifiers + particle systems; `is_baked` flags.
- **files**: `bpy.data.libraries`, images, cache files, sounds, fonts.
- **perf**: depsgraph timing.

## Bridge / loader

- `blender/host.py` — process singleton facade: `progress`, request queue,
  server, `open_panel()` (starts server + registers the pump timer +
  `webbrowser.open`). Mirrors `bridge/__init__.py` facades.
- `src/plugin/blender/__init__.py` — the addon: `bl_info`, an Operator
  "Overseer: Open" (and a menu/N-panel button) that calls `host.open_panel()`,
  plus `register()`/`unregister()`. Inserts its own dir on `sys.path` so
  `import overseer` resolves the bundled package.

## Packaging & deploy

The installable addon folder bundles `overseer/` (this whole package incl.
`blender/`), the Vite `web/` build, and `vendor/` (Pillow), next to the addon
`__init__.py`. Dev deploy mirrors those into Blender's
`scripts/addons/overseer/` (see `.claude/skills/deploy`). Zip layout mirrors
the C4D release zip.

## Testing (no Blender in CI)

`bpy` is unavailable in CI, exactly like `c4d`. Two tiers:
1. Pure logic (`core/`, `naming/`, `core/webio.py`) — normal pytest.
2. Blender adapter/webapi — a **fake `bpy`** stub (`tests/fakebpy/`) injected
   into `sys.modules` lets us unit-test tree building, classification,
   collection assignment and the webapi op registry against synthetic scenes.
   Keep the fake minimal; only model what the code under test touches.

## Conventions

- Only `blender/` imports `bpy`; nothing else may (tests import the rest
  without Blender).
- One undo step per mutation: do all edits, then a single `doc.undo_push(msg)`.
- Every slow op publishes a progress label (reuse `_OP_LABELS` from the C4D
  webapi — copied into `blender/webapi.py`) and clears it in `finally`.
- Cross-request caches live on the `overseer` package (never purged) keyed on
  `BScene.dirty()`; mutating ops call `invalidate_scene_cache()`.
- Code & comments in ENGLISH (see docs/ai/rules.md).
</invoke>
