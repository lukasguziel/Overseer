# sceneorg.core — pure scene-domain logic

The deterministic heart of Overseer: hierarchy model, analysis, and the
planners that turn a `SceneTree` into rename / reparent / layer operations. This
package NEVER imports `c4d`, so every module here runs and is fully tested in CI.

## Modules

### model.py
`SceneNode` / `SceneTree` dataclasses — the pure hierarchy (name, type, category,
guid, point/poly counts, layer, parent/children). Category constants
(`CAT_LIGHT` ... `CAT_OTHER`, `ALL_CATEGORIES`). Nodes cache subtree poly/point
sums recursively; `walk()`, `descendants()`, `ancestors()`, `top_group()`,
`path`. `parent` is a back-reference (not repr'd) — the model is by-reference.

### ops.py
The planners. `Writer`/`Operation` ABCs plus `RenameOp` / `ReparentOp` /
`LayerOp` (each carries its `node` and a `to_dict()`). `plan_renames()` buckets
siblings by parent, applies the `NamingConvention`, and dedupes within a bucket;
`_rename_rules()` reconstructs which rules fired (casing/numbering/prefix/unique)
for the UI. `plan_reparents()` honours safe-only + tidy; `plan_layers()` skips
objects already on their target layer; `plan_layer_suggestions()` inherits the
nearest ancestor's layer. `is_safe_to_reparent()`: only root/Null children move.

### analyzer.py
`SceneAnalyzer` walks a `SceneTree` once to produce a `SceneReport`
(counts, categories, poly/point stats, multi-language name detection across all
bundled dictionary packs).

### pipeline.py
`plan_combined()` runs naming + structure + layers in a single tree read and
returns a `CombinedPlan`; `filter_accepted()` narrows it to accepted rows.
Backend of the one-button plan_all/apply_all flow.

### keeps.py
Per-section "accepted as-is" lists. `empty_keeps`/`normalize_keeps`/
`set_section_keeps` normalise a config `keeps` value into a sorted, deduped map;
`filter_kept` partitions plan items into (todo, kept) by key membership.

### journal.py
Undo/apply journal helpers: `normalize_entry`/`normalize_journal`,
`merge_journals`, `items_to_revert`, `mark_reverted`, `set_entry`. Pure list/dict
transforms — no side effects.

### layers.py
`LayerInfo` / `LayerMismatch` plus `build_layer_report()` and
`find_layer_mismatches()` — compares layer metadata and object layer assignments
against the expected scheme.

### defaults.py
Constant tables: renderer light/camera IDs, `CATEGORY_LAYERS`, `TYPE_LAYERS`,
`DEFAULT_LAYER_SCHEME`, `LAYER_COLORS`.

### textures.py
Texture/VRAM analysis. `ImageInfo`, `vram_bytes()` (mipmap factor 4/3),
`aggregate()`, `resize_decision()`/`resize_target()`/`scaled_dims()`, and
per-format header readers (`_png_info`, `_jpeg_info`, `_tiff_info`, `_exr_info`,
...) with a Pillow fast path (`_pillow_info`) and a dependency-free header
fallback (`_header_info`).

### imagesize.py
Dependency-free image dimension probing by format (`image_size()` plus
`_exr_size`, `_webp_size`, `_tiff_size`, `_jpeg_size`, `_hdr_size`, `_tga_size`);
`resolution_tag()` buckets pixel counts into labels.

### files_logic.py
Asset/texture path logic: `file_ext`, `is_image`, `classify_kind`,
`relocatable()` (can a path be relinked), and `summarize()`. `IMAGE_EXTS` set.

### gens_logic.py
Generator-parameter summaries: `value_distribution`, `dominant_value`,
`is_uniform`, `summarize` (uses `_hashable` to bucket unhashable values).

### sims_logic.py
Simulation scan. `SimHit` plus predicates `is_active_hidden`, `is_unbaked`,
`is_disabled_leftover`; `compute_findings`/`summarize`/`scan_result`.

### tags_logic.py
Tag helpers: `deg_from_rad`, `dominant_angle`, `DEFAULT_PHONG_ANGLE_DEG`;
`merge_selection_types` folds the point/polygon/edge selection tag entries of
a tags scan into one "Selection" entry (kind stamped per tag, `type_ids` on
the entry).

### ui_settings_logic.py
UI-state persistence: `PERSISTED_KEYS`, `project_slug()` (via `_slug_text`),
`sanitize_ui()` to coerce arbitrary input into a safe settings dict.

### __init__.py
Empty package marker.

## Conventions & gotchas

- Never import `c4d` here — this package is the CI-testable domain layer. Host
  glue lives in `sceneorg/cinema/`.
- The model is a mutable, by-reference dataclass graph (`parent` back-refs);
  planners read it but return `Operation` objects rather than mutating the tree.
- Planners only touch objects whose parent is root or a Null (`is_safe_to_reparent`) —
  generator/deformer children are left alone.
- Layer/rename planners are idempotent: rows already at their target are skipped
  so applied items drop out of the next preview.
- Texture/imagesize readers must work without Pillow — always keep the
  header-parsing fallback path valid.

Per-module prose: see the mirrored files under `docs/sceneorg/core/`.
