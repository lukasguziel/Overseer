# cinema/adapter.py

C4D adapter: builds a pure `SceneTree` from a document and writes operations
(rename/reparent/layer) back with undo support. This is the ONLY domain module
that imports `c4d`, and it is never loaded by the unit tests. All methods run on
the C4D main thread.

## Module constants

- `LAYER_COLORS` — RGB (0..1) colors applied to auto-created type layers
  (Lights/Cameras/Proxies/Splines).
- `KNOWN_TYPES` — map of C4D object type ids to friendly names, incl. MoGraph
  cloner/matrix/fracture/text ids.
- `RS_LIGHT_IDS` / `RS_CAMERA_IDS` — Redshift light/camera object type ids used
  by `classify`.

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
  missing textures.
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
- `scan_layers()` — metadata per layer incl. empty ones: color and the flags an
  artist manages — solo (S), view (editor dot V), render (R), locked (L), plus
  the per-layer `materials` / `tags` reference counts (from
  `c4d.ID_LAYER_LINK`). Object counts are added later by the analyzer.
  Best-effort; an unreadable flag defaults to True except `locked`.
- `delete_empty_layers()` / `delete_layer(name)` — remove layers that nothing
  references (no objects, materials or tags), in ONE undo step. `delete_layer`
  is a no-op guard when the named layer is not actually empty. Emptiness is
  judged against the same object/material/tag scan `scan_layers` uses.
- `delete_material(name)` — deletes unused materials with that name (undoable).
  Safety: only removes materials not assigned to any texture tag, even if a
  same-named material is in use.
- `delete_unused_materials()` — deletes ALL currently unused materials in ONE
  undo step. Same name-based safety.
- `ensure_group_path(path, created, canonical=None)` — find or create the null
  chain for a group path like "Room/Furniture". Each segment is matched among
  the previous one's children (top level: document roots), reusing existing
  containers, alias-aware via `canonical`. Missing segments are created
  (undoable). `_match_group` matches a null by case-insensitive name or via the
  canonical resolver, so an existing "Lichter" is reused for "Lights".
- `_find_or_create_group(name, created)` — thin wrapper over `ensure_group_path`.
- `apply_renames(renames)` — renames objects by guid in one undo step; skips
  guids no longer in the map.
- `_find_or_create_layer(name, created, cache)` — finds or creates a colored
  layer under the layer root, cached by name.
- `apply_layers(layerops)` — assigns type-axis layers without touching the
  hierarchy. Layers created on demand (colored). Only the layer assignment
  changes; the spatial null structure stays untouched.
- `_do_reparents(reparents, created, canonical)` — reparent ops WITHOUT their own
  undo bracket (shared by `apply_bundle`). Preserves world position by re-setting
  the global matrix after `InsertUnderLast`. Skips moving an object into itself.
- `apply_reparents(reparents, canonical=None)` — `_do_reparents` wrapped in one
  undo step.
- `apply_bundle(renames, reparents, layerops, canonical=None)` — applies naming +
  structure + layers in ONE undo step (single Ctrl+Z). Order: renames first (by
  guid, order-independent), then reparents (may create group chains), then
  layers. Backend of the one-button `apply_all` flow.
- `apply_plan(operations)` — executes a deterministic restructuring plan (1 undo
  step) written by the skill. Ops (order matters): `group`/`rename`/`move`/
  `layer`. `target`/`under`/`into` reference either an existing export `guid`
  (int) or a plan-local `$id` (str) of a group created earlier in the plan.
  Collects per-op errors instead of aborting (the `# noqa: BLE001` broad-except
  is intentional). After this call the guids are stale, so `build_tree()` must
  run again.

## Change log & revert
- Every write method resets and fills `self.last_changes` — a list of
  `{sid, name, field, before, after}` where `field` is `name`/`layer`/`parent`.
  `sid` is the C4D-stable object id (`stable_id(op)` = `op.GetGUID()`), captured
  so a change can be reverted later; `webapi` persists these as one history
  entry per apply. `build_tree()` also indexes objects by `sid` in `_by_sid`.
- `revert(items, canonical)` — restores each item's `before` value in ONE undo
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
- `texture_resize(paths, percent)` — write resized COPIES (`_<percent>` suffix)
  next to the originals and relink the shaders (`core/textures.resize_file`,
  Pillow or the pure PNG path). Originals are never overwritten; each source is
  copied once; per-file skips carry a note so the batch never fails as a whole.
  Relinks are journaled as `texpath` changes.
- `revert` handles the `texpath` field: it rewrites the current (after) path
  back to the recorded (before) path across every shader holding it — so resize
  and repath are selectively revertible through the M2 history.
