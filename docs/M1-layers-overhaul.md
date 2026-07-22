# M1 — Layers overhaul (implementation plan & record)

Status: **shipped**. All four ROADMAP M1 items are done and ticked.
Quality gates green: `pytest` 110 passed, `ruff` clean, `pnpm test` 16 passed,
`pnpm run build` OK. Deployed to Cinema 4D 2024 (user prefs).

## Scope (the four features)

1. **Delete empty layers** — single layer + "delete all empty", one undo step.
2. **True emptiness** — a layer is empty only when NO objects, NO materials and
   NO tags reference it (`c4d.ID_LAYER_LINK` on materials and tags).
3. **Layer suggestions for unassigned objects** — object with no layer inherits
   its nearest ancestor's layer, rendered as accept/reject rows.
4. **Intentional-mismatch finding** — parent on layer A, child on layer B is an
   informational finding only (never auto-applied), acceptable via keeps.

## What changed

### Pure domain logic (no c4d)
- **New `src/overseer/core/layers/report.py`**
  - `LayerInfo` dataclass: `object_count` / `material_count` / `tag_count` /
    `poly_count`; `empty` is true only when nothing references the layer.
  - `build_layer_report(layer_meta, object_counts, poly_counts, no_layer)` —
    assembles `{layers, no_layer, total_layers, empty_layers}` (replaced the old
    inline `_merge_layers` body in webapi).
  - `LayerMismatch` + `find_layer_mismatches(tree, keep)` — child-vs-parent
    layer differences, keeps-filtered, informational.
- **`src/overseer/core/organize/ops.py`** — `plan_layer_suggestions(tree, scope, keep)`
  returns `LayerOp`s inheriting the nearest ancestor's layer.

### c4d adapter (`src/overseer/cinema/adapter.py`)
- `scan_layers()` now also returns per-layer `materials` / `tags` counts via
  `c4d.ID_LAYER_LINK` (helpers `_layer_ref_counts`, `_linked_layer_name`,
  `_layer_object_counts`).
- New `delete_empty_layers()` and `delete_layer(name)` — remove only truly-empty
  layers, one undo step; `delete_layer` refuses a non-empty layer.

### JSON API (`src/overseer/cinema/webapi.py`)
All are POST to the single JSON handler, selected by the `op` field:

| op | payload | response |
| --- | --- | --- |
| `plan_layer_suggestions` | `{settings}` | `{ok, count, diff:[{guid,name,layer}]}` |
| `layer_mismatches` | `{settings}` | `{ok, count, findings:[{guid,name,path,parent,parent_layer,child_layer}]}` |
| `delete_layer` | `{name}` | `{ok, deleted}` |
| `delete_empty_layers` | `{}` | `{ok, deleted}` |

Registered in `_OP_LABELS` and `_MUTATING_OPS`. Mismatch accept-as-is reuses the
existing `set_keeps` section `layers`.

### Frontend
- `types.ts`: `LayerInfo` gains `materials` / `tags`; new `LayerMismatch`.
- `hooks/useOrganizer.ts`: state `layerSuggestions` / `layerMismatches`,
  `reloadLayerExtras`, a `usePreview('layers', ...)`, and `doDeleteLayer` /
  `doDeleteEmptyLayers`.
- `components/LayerTree.tsx`: shows mat/tag counts + per-empty-layer delete.
- `tabs/LayersTab.tsx`: "Delete N empty" button, ancestor-suggestion one-click
  assign in the no-layer worklist, and the informational "Mixed-layer
  hierarchies" card with accept-as-is.

### Tests / docs
- New `tests/test_layers.py` (7 tests): emptiness classification, mat/tag
  surfacing, ancestor suggestion + scope/keep skips, mismatch finding +
  kept/unassigned filtering.
- New `docs/overseer/core/layers.md`; updated `ops.md`, `cinema/adapter.md`,
  `cinema/webapi.md`; four M1 boxes ticked in `docs/ROADMAP.md`.

## Restart note
Only `overseer` logic + frontend changed (no `bridge.py` / `.pyp` signature
change) — backend hot-reloads on the next command click; reload the browser for
the new UI. No C4D restart needed.
