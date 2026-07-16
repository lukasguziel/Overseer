# cinema/adapter/ (package)

C4D adapter: builds a pure `SceneTree` from a document and writes operations
(rename/reparent/layer) back with undo support. Never loaded by the unit tests.
All methods run on the C4D main thread.

One file per domain class; `SceneAdapter` composes the mixins, so `self` spans
all of them (state lives in `SceneAdapter.__init__`: `doc`, `_by_guid`,
`_by_sid`, selection sets, `last_changes`):

```
adapter/
  __init__.py    exports SceneAdapter, load_journal, save_journal
  readers.py     module-level c4d readers (type_name/own_geo/classify/
                 layer_name/stable_id/editor_hidden, _SAVE_FILTERS)
  scene.py       SceneAdapter(MaterialOps, PreviewOps, TexturePathOps,
                 TextureResizeOps, LayerOps, ApplyOps): build_tree/focus/
                 selection
  materials.py   MaterialOps: usage scan, unused/missing, delete
  previews.py    PreviewOps: material/texture thumbnail rendering
  texpaths.py    TexturePathOps: texture reference scan + path rewriting
                 (incl. maxon node-graph ports)
  texresize.py   TextureResizeOps: resized copies + relink
  layers.py      LayerOps: layer scan/delete/colors, find-or-create
  apply.py       ApplyOps: renames/reparents/layers/bundle/plan/revert
  journal.py     journal persistence (document container + sidecar)
```

## Module constants

- `LAYER_COLORS` — RGB (0..1) colors applied to auto-created type layers
  (Lights/Cameras/Proxies/Splines).
- `KNOWN_TYPES` — map of C4D object type ids to friendly names, incl. MoGraph
  cloner/matrix/fracture/text ids.
- `RS_LIGHT_IDS` / `RS_CAMERA_IDS` — Redshift light/camera object type ids used
  by `classify`.
- `_SAVE_FILTERS` — file extension -> the C4D image writer symbol that saves it
  (`FILTER_PNG`, `FILTER_JPG`, …), built by `_save_filters()`. Each symbol is
  resolved through `getattr(c4d, ...)` so a filter this C4D version does not
  expose simply drops out of the table instead of breaking the import.

## Module functions

- `type_name(op)` — friendly type name: known map first, then `GetTypeName()`,
  else `type_<id>`.
- `_virtual_geo(op)` — sums (points, polygons) across a cache/deform subtree of
  virtual objects. Only reads counter ints, never iterates individual polys, so
  it stays fast even with millions of polygons.
- `own_geo(op)` — (points, polygons) of ONE scene object without scene-graph
  children. Editable poly → direct counters; generators (Cube/Cloner/Sweep/
  MoGraph) → geometry from their cache, so primitives get a realistic count
  instead of 0.
- `classify(op)` — maps an object to a category (camera/light/null/spline/mesh/
  other). Recognizes Redshift lights/cameras by id and German/English keywords
  ("licht"/"kamera") in the type name.
- `layer_name(op)` — name of the C4D layer the object is assigned to, or None.
- `editor_hidden(op)` — True only if the object's OWN editor visibility dot is
  explicitly MODE_OFF. Default/MODE_UNDEF and MODE_ON count as visible;
  inherited hiding from a hidden parent is resolved by the caller while walking
  the tree. Best-effort.

## SceneAdapter

Bidirectional bridge document <-> SceneTree.

- `__init__(doc)` — holds the doc, a guid→object map, and captured selection
  sets. Selection is captured during tree construction via the stable
  `BIT_ACTIVE` flag; `GetActiveObjects`/`id(op)` does NOT work because C4D
  returns fresh Python wrappers on every API call so `id()` never matches.
- `count_objects()` — fast object count (no name/geometry reads) for progress
  totals.
- `build_tree(progress=None)` — builds the `SceneTree`; captures selection and
  effective (inherited) editor visibility per node. `progress(current, total,
  detail)` fires every ~50 objects so long scans can drive a preloader. Must be
  called before `selected_guids`, `focus`, and any guid-based apply.
- `selected_guids(include_children=True)` — guids of selected objects (optionally
  incl. children). Only valid after `build_tree()`.
- `focus(guid)` — selects the object exclusively and frames the active camera on
  its bounding box (like pressing "S"). Sets the camera matrix directly rather
  than `CallCommand(Frame)`, which would no-op when the web panel has focus.
  Unfolds the ancestor chain (`BIT_OFOLD`) and calls the undocumented but stable
  Object Manager "Scroll To First Active" command id `100004769`. Nulls/splines/
  cameras with no volume get a default radius of 100. Main thread, after
  `build_tree()`.
- `_used_material_names()` — names of all materials assigned via texture tags.
  Tracked by NAME because wrapper identity/`id()` is not stable. Best-effort.
- `scan_materials()` — overview dict: total, unused (not assigned by name),
  missing textures. Plugin-internal helper materials (Octane's `__octanetemp__`
  etc., detected by `core/materials_logic.is_internal_material`) are skipped
  everywhere — never listed as unused/missing and never deletable, because the
  renderer recreates or needs them.
- `_iter_bitmap_shaders(mat)` — yields every Xbitmap shader in a material incl.
  nested ones (shaders form a tree via GetNext siblings / GetDown children), so
  a bitmap buried in a Layer/Fusion shader is found. Best-effort.
- `scan_textures()` — every bitmap texture split absolute vs relative. Absolute
  paths break when the project moves machines, so they are the ones worth fixing.
  `relocatable` marks an absolute texture whose file physically lives under the
  project folder → can be rewritten relative without moving files. Dedupes disk
  footprint per physical file (shared maps counted once).
- `make_textures_relative(materials=None)` — rewrites relocatable absolute paths
  to project-relative ones (undoable). Nothing is copied/moved, only the stored
  filename is shortened. Errors if the project is unsaved (no folder to relate
  to). `materials` optionally restricts to named materials.
- `_collect_candidates(only, paths=None)` — the collect candidate list:
  stored-absolute texture refs whose file lives OUTSIDE the project folder, as
  `(raw, resolved, owners)`. Sourced from `GetAllAssetsNew` (stored form via
  `_stored_path_for`) merged with an `_iter_bitmap_shaders` walk, so node
  materials (Redshift & co) are found too — the old shader-only walk missed
  them and the collect button silently did nothing. `paths` narrows to the
  given raw/resolved paths (`_same_path`-tolerant) — the per-row Copy &
  relink. Also returns `diag` strings for every absolute ref that is NOT
  collectable (file missing on disk / already inside the project).
- `texture_owners(path)` — names of every material holding the path, checked
  per material via `_find_path_params` (description params incl. the shader
  tree) with a `_node_path_ports` fallback (node-space ports). Backs the
  per-texture collect modal: the artist sees WHICH materials the relink will
  touch before confirming — `GetAllAssetsNew` alone under-reports (one owner
  per file), so the scan's single `material` column is not the whole truth.
- `collect_textures(materials=None, subdir="tex", paths=None)` — copies the
  candidates into `<project>/<subdir>` (created on demand; a failure to
  create it is a hard `error`) and relinks every reference to
  `<subdir>/<file>`:
  `_write_path_refs` per recorded owner PLUS an unconditional
  `_write_path_anywhere` sweep (relink in ONE undo step; the file copy itself
  is not undoable). The sweep is not a fallback: `GetAllAssetsNew` may report
  only one owner for a file shared by several materials, so a sweep that only
  ran when nothing wrote left the other materials absolute — the texture then
  showed up twice in the scan (relative + absolute). Name clashes in the
  target folder get a `_N` suffix unless the bytes already match. `diag`
  also records copy failures (with the OS error) and copied-but-not-relinked
  refs; the web UI shows the reasons verbatim instead of a silent no-op.
- `scan_layers()` — metadata per layer incl. empty ones: color and the flags an
  artist manages — solo (S), view (editor dot V), render (R), locked (L), plus
  the per-layer `materials` / `tags` reference counts (from
  `c4d.ID_LAYER_LINK`). Object counts are added later by the analyzer.
  Best-effort; an unreadable flag defaults to True except `locked`.
- `delete_empty_layers()` / `delete_layer(name)` — remove layers that nothing
  references (no objects, materials or tags), in ONE undo step. `delete_layer`
  is a no-op guard when the named layer is not actually empty. Emptiness is
  judged against the same object/material/tag scan `scan_layers` uses.
- `set_layer_colors(colors)` — set each named layer's color (0..1 RGB) in ONE
  undo step.
- `delete_material(name)` — deletes unused materials with that name (undoable).
  Safety: only removes materials not assigned to any texture tag, even if a
  same-named material is in use.
- `delete_unused_materials()` — deletes ALL currently unused materials in ONE
  undo step. Same name-based safety.
- `ensure_group_path(path, created)` — find or create the null
  chain for a group path like "Room/Furniture". Each segment is matched among
  the previous one's children (top level: document roots), reusing existing
  containers (case-insensitive name match). Missing segments are created
  (undoable).
- `_find_or_create_group(name, created)` — thin wrapper over `ensure_group_path`.
- `apply_renames(renames)` — renames objects by guid in one undo step; skips
  guids no longer in the map.
- `_find_or_create_layer(name, created, cache)` — finds or creates a colored
  layer under the layer root, cached by name.
- `apply_layers(layerops)` — assigns type-axis layers without touching the
  hierarchy. Layers created on demand (colored). Only the layer assignment
  changes; the spatial null structure stays untouched.
- `_do_reparents(reparents, created)` — reparent ops WITHOUT their own
  undo bracket. Preserves world position by re-setting
  the global matrix after `InsertUnderLast`. Skips moving an object into itself.
- `apply_reparents(reparents)` — `_do_reparents` wrapped in one
  undo step (backend of the Assets tab's "move to group" batch action).

## Change log & revert
- Every write method resets and fills `self.last_changes` — a list of
  `{sid, name, field, before, after}` where `field` is `name`/`layer`/`parent`.
  `sid` is the C4D-stable object id (`stable_id(op)` = `op.GetGUID()`), captured
  so a change can be reverted later; `webapi` persists these as one history
  entry per apply. `build_tree()` also indexes objects by `sid` in `_by_sid`.
- `revert(items)` — restores each item's `before` value in ONE undo
  step (name/layer/parent). Objects are resolved by `sid`, with a fallback to
  matching the current object name (`_resolve_change`), so an in-session revert
  is reliable; after reload the id map is rebuilt from the live scene. Returns
  `{reverted, missing, results}` where `results` is parallel to `items` with a
  per-op `status` (`reverted` / `missing` / `skipped`) — a deleted/renamed
  target is skipped, never aborting the rest (M2 robustness).

## Journal persistence (module-level, M2)
- `load_journal(doc, fallback_path)` — the scene's change journal, reconciled
  (`journal.merge_journals`) from the document's private BaseContainer
  (`DOC_JOURNAL_ID`, travels inside the .c4d), the sidecar
  `<project>/<name>.sohistory.json`, and the machine-local `fallback_path` for
  unsaved scenes.
- `save_journal(doc, entries, fallback_path)` — writes the BaseContainer copy
  (`SetChanged` so the save picks it up) plus the sidecar (or the fallback file
  when the scene is unsaved). Both go through `journal.normalize_journal`.

## Textures (M4 additions)

- `scan_textures(include_hidden)` now enriches every row with the
  `core/textures.analyze_image` metadata (`bit_depth`, `channels`, `has_alpha`,
  `greyscale`, `colorspace`, `vram`) and adds a document-level `total_vram`
  (each physical file counted once) that feeds the Overview texture-budget card.
- `texture_repath(paths, mode, material=None)` — convert references between
  relative and absolute form (`_repath_targets` decides what is convertible:
  make-absolute needs a resolvable file, make-relative needs the file under the
  project). One undo step; every rewrite is journaled as a `texpath` change.
  When a path produces no target at all (missing file, already in the requested
  form, outside the project), `_repath_diag` returns a plain-language reason per
  path in the `diag` list — otherwise a no-op looks like a broken button. If
  some paths had owners but none held the string, the rewrite still falls
  through to `_write_path_anywhere` document-wide rather than reporting "nothing
  changed", and any remaining mismatch is diagnosed via `_node_path_values`.
- `texture_resize(paths, percent)` — write resized COPIES (`_<percent>` suffix)
  next to the originals and relink the shaders (`core/textures.resize_file`,
  Pillow or the pure PNG path). Originals are never overwritten; each source is
  copied once; per-file skips carry a note so the batch never fails as a whole.
  Relinks are journaled as `texpath` changes. Pillow is tried FIRST (LANCZOS,
  keeps alpha, bit depth and the ICC profile; it ships with the plugin under
  `src/vendor`); `_host_resize` is the fallback when Pillow is absent or refuses
  the format (e.g. EXR, which Cinema handles natively). A file is only counted
  as "resized" once the material is actually relinked to the copy — a copy on
  disk whose shader still points at the original is reported "skipped", not
  "resized", because nothing in the scene got lighter.

### Host bitmap resize (`_host_resize`)

Downscales an image with Cinema 4D's own bitmap engine — this is why the plugin
needs no Pillow: C4D reads and writes every texture format it can load,
in-process, in C++. Gotchas baked in:

- `ScaleIt` only touches the colour channels, so a map WITH an alpha channel is
  REFUSED here and left to Pillow — silently dropping a mask would be worse than
  not resizing at all.
- Bit depth is preserved end to end: the work bitmap keeps the source depth
  (`GetBt`) and deep sources are SAVED with 32-bit channels, so an HDR/EXR stays
  float (no tonemap, no 8-bit) and a 16-bit TIFF does not come back crushed.
  8-bit layouts are 8 (grey) or 24 (RGB) bits per pixel; anything else (16-bit
  grey, float grey, 16-bit/float RGB) must be written with
  `SAVEBIT_32BITCHANNELS` or the writer quietly clamps to 8-bit. Writers without
  deep support (JPG/BMP) ignore the flag.
- `ScaleBicubic` is used where available (visibly better on downscales than the
  sampled box filter), with `ScaleIt` as the fallback.
- `revert` handles the `texpath` field: it rewrites the current (after) path
  back to the recorded (before) path across every shader holding it — so resize
  and repath are selectively revertible through the M2 history.

## Node-material path writes

`_write_path_refs` covers classic references (Xbitmap `BITMAPSHADER_FILENAME`
plus any string description parameter). Node materials (Redshift, the standard
node space, Arnold …) keep their texture path inside a node PORT, which
`GetAllAssetsNew` reports as an asset but the description walk cannot write —
that used to leave "missing" rows that clear/relink/repath silently skipped.

`_write_path_refs` therefore ALWAYS also runs `_write_node_paths` for a
material owner — not only when the classic walk wrote nothing, because a
material can hold the same path in a description parameter AND a node port,
and rewriting just one of them leaves a stale absolute reference behind.
`_write_node_paths` walks every node space the material has
(`_NODE_SPACE_IDS`), recurses all input ports (bundles included), matches
`maxon.Url` / string values via `_same_path` (URLs converted with
`_url_to_syspath`), and writes the new value inside a graph transaction
(`maxon.Url` values get `_syspath_to_url_string`, e.g. `file:///Q:/...`).
If the direct owner is not the holding material, a last-resort pass tries every
document material. Undo: `AddUndo(UNDOTYPE_CHANGE, mat)` before the transaction,
inside the caller's existing `StartUndo/EndUndo` bracket.

### Path-write helpers

- `_stored_path_for(owner, resolved)` — returns the path the material ACTUALLY
  stores for a texture. `GetAllAssetsNew` reports the RESOLVED path — always
  absolute, even for a material that stores `tex/wall.png`. Taking that as the
  reference is what made every map look absolute (relative: 0) and made a
  rewrite search the shaders for a string that is not in them ("no parameter
  held the path"). So it matches by FILE NAME and returns the string the shader
  really holds; the resolved path stays the fallback. `_texture_refs` relies on
  this so absolute/relative classification and rewrites see the stored string,
  not the resolved one.
- `_owner_index()` — maps a stored path to its owners. Keyed by BOTH the stored
  path (what the UI sends back) and the resolved path, so an owner is found
  either way.
- `_node_space_ids()` — every node space registered in this Cinema, read from
  the `maxon.registries.NodeSpaces` REGISTRY (renderer-agnostic). `_NODE_SPACE_IDS`
  (Redshift / standard / Arnold / Vantage) is only a hardcoded FALLBACK: relying
  on it alone means every renderer we did not think of — Octane, Corona, next
  year's — silently gets no texture rewrite at all. Ask the host what it has
  instead of guessing.
- `_write_path_anywhere(raw, new_path)` — rewrites a reference we have no owner
  for. `GetAllAssetsNew` does not report an owner for every reference (node
  materials of third-party renderers in particular); with no owner the owner
  loop never runs, and every fallback inside `_write_path_refs` lives behind
  that loop, so the path was counted as "skipped" while it sat right there in
  the scene. This walks the materials/shaders itself and ALWAYS also runs
  `_write_node_paths` across every document material (same
  param-plus-node-port reasoning as `_write_path_refs`).
- `_node_path_values(limit=6)` — diagnostic only: every path-ish value the node
  graphs actually hold. When a rewrite finds no port for a path, the useful
  question is what the graph DOES store for it (a relative string? a `file://`
  url? an asset-db id?) — guessing that from the outside is how an afternoon
  disappears, so `texture_repath` surfaces it in the `diag` output.
