# overseer.core — pure scene-domain logic, one package per area

The deterministic heart of Overseer. This package NEVER imports `c4d` or
`bpy`, so every module here runs and is fully tested in CI. It is organized
**per area**: each area package defines the normalized data model and result
shapes ("how it is displayed in the end"); the host packages (`cinema/`,
`blender/`) mirror the same area names and only gather their host-specific
data into those shapes.

## Area packages

### scene/
`model.py` — `SceneNode` / `SceneTree` dataclasses, the pure hierarchy (name,
type, category, guid, point/poly counts, layer, parent/children). Category
constants (`CAT_LIGHT` ... `CAT_OTHER`, `ALL_CATEGORIES`). Nodes cache subtree
poly/point sums recursively; `walk()`, `descendants()`, `ancestors()`,
`top_group()`, `path`. `parent` is a back-reference — the model is by-reference.
`analyzer.py` — `SceneAnalyzer` walks a `SceneTree` once to produce a
`SceneReport` (counts, categories, poly/point stats, multi-language name
detection across all bundled dictionary packs).

### naming/
The naming convention pipeline (see [naming.md](naming.md)): `casing.py`
(tokenizer, casing detection, language heuristic), `convention.py`
(`NamingConvention`, `disambiguate()`), `detect.py` (auto-detect existing
scheme), `translate.py` (language-only rename proposals), `translations.py`
(DE<->EN dictionary + `add_translations()`) plus the `data/` dictionary packs.

### organize/
`ops.py` — the planners. `Writer`/`Operation` ABCs plus `RenameOp` /
`ReparentOp` / `LayerOp` (each carries its `node` and a `to_dict()`).
`plan_renames()` buckets siblings by parent, applies the `NamingConvention`,
and dedupes within a bucket; `plan_reparents()` honours safe-only + tidy;
`plan_layers()` skips objects already on their target layer;
`plan_layer_suggestions()` inherits the nearest ancestor's layer.
`keeps.py` — per-section "accepted as-is" lists (`filter_kept`,
`set_section_keeps`, `normalize_keeps`).
`journal.py` — undo/apply journal helpers (`normalize_journal`,
`merge_journals`, `items_to_revert`, `mark_reverted`). Pure transforms.

### layers/
`report.py` — `LayerInfo` / `LayerMismatch` plus `build_layer_report()` and
`find_layer_mismatches()` — compares layer metadata and object layer
assignments against the expected scheme.

### materials/
`logic.py` — `is_internal_material()`: dunder-named plugin helpers (Octane's
`__octanetemp__` etc.) are never listed as unused and never deleted.

### textures/
`analysis.py` — texture/VRAM analysis: `ImageInfo`, `vram_bytes()`,
`aggregate()`, `resize_decision()`/`resize_target()`/`scaled_dims()` with a
Pillow fast path and a dependency-free header fallback. `imagesize.py` —
dependency-free image dimension probing by format; `resolution_tag()`.
`thumbs.py` — Pillow-rendered texture thumbnails (safe off the host main
thread).

### files/ · generators/ · sims/ · tags/ · perf/
Each audit area ships two modules:
- `logic.py` — the pure result shaping (`files`: `classify_kind`/`relocatable`/
  `summarize`; `generators`: `value_distribution`/`summarize`; `sims`:
  `SimHit` + findings + `scan_result`; `tags`: `dominant_angle`,
  `merge_selection_types`; `perf`: `median`/`rank`/`overlap_ratio`).
- `audit.py` — the shared `Audit` base class for the area: it owns the op
  dispatch and the display shaping, and declares the host-specific read/apply
  primitives as `@abstractmethod`s. A host provides a subclass (in
  `cinema/<area>.py` / `blender/<area>.py`) exposing a ready `AUDIT` instance.

### settings/
`logic.py` — UI-state persistence rules: `PERSISTED_KEYS`, `project_slug()`,
`sanitize_ui()`. `io.py` — per-project + global UI-state file IO.

### hostapi/
The host-abstraction layer (see [hostapi.md](hostapi.md)): `ports.py` —
`SceneHost`/`SceneAdapter`/`Audit`/`HostContext` ABCs; `webapi.py` — the ONE
shared JSON op layer (all `_op_*` handlers, host-neutral, bound to a host via
`WebApi(ctx)`).

### Cross-area root modules
`defaults.py` — constant tables (renderer ids, `DEFAULT_LAYER_SCHEME`,
`LAYER_COLORS`, update profiles, ports). `webio.py` — host-neutral web/data-dir
IO helpers.

## Area base classes: the shared workflow is CODE, not convention

Each adapter area ships a `base.py` with an `<Area>Base` ABC (template-method
pattern, all inheriting `core/items.py::ItemsBase` for progress-chunked
`each()` loops): the base owns the genuinely shared workflow (e.g.
`MaterialsBase.scan_materials` — the whole classification loop;
`LayersBase.scan_layers`; `TexturePathsBase.scan_textures`;
`OrganizeBase.rename_object`/`apply_renames` + the change log) and declares
host reads/writes as abstract `get_*`/`set_*` primitives. A host implements
`Cinema<Area>` / `Blender<Area>` with ONLY the primitives; where a host
genuinely needs a different workflow it OVERRIDES the base method and that
override stays visible (Blender's two-phase `apply_renames`, its
`is_internal` prefix rule). `hostapi.SceneAdapter` is the sum of these bases.
Each base has a fake-host unit test in `tests/core/<area>/test_<area>_base.py`.

## Row factories: the displayed shape is CODE, not convention

Every JSON row/envelope the frontend sees is built by a factory in its area —
hosts fill fields, they never hand-assemble result dicts:
`layers.report.layer_entry`, `tags.logic.type_entry`/`object_row`/`scan_result`,
`files.logic.file_entry`/`scan_result`, `generators.logic.value_entry`/
`param_row`/`type_row`/`scan_result`, `perf.logic.measure_row`/`finish_scan`,
`materials.logic.scan_result`, `textures.analysis.texture_row`/
`texture_scan_result`, `organize.journal.change_item` (the revert item shape).
A new host cannot drift from the frozen frontend contract, and the shapes are
unit-tested here without any host SDK.

## Conventions & gotchas

- Never import `c4d`/`bpy` here — this package is the CI-testable domain layer.
  Host glue lives in `overseer/cinema/` and `overseer/blender/`.
- The model is a mutable, by-reference dataclass graph (`parent` back-refs);
  planners read it but return `Operation` objects rather than mutating the tree.
- Planners only touch objects whose parent is root or a Null
  (`is_safe_to_reparent`) — generator/deformer children are left alone.
- Layer/rename planners are idempotent: rows already at their target are
  skipped so applied items drop out of the next preview.
- Texture/imagesize readers must work without Pillow — always keep the
  header-parsing fallback path valid.
- A new audit area = `core/<area>/logic.py` + `core/<area>/audit.py`, then one
  `<area>.py` per host subclassing the audit. `tests/test_import_graph.py` and
  the per-host mirror tests enforce the layout.

Per-module prose: see the mirrored files under `docs/overseer/core/`.
