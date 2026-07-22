# core/layers

Pure layer reporting and consistency findings. No `c4d`. The c4d-bound
[cinema/adapter](../cinema/adapter.md) scans the document (objects, materials
and tags) and feeds raw counts in here; the assembled dicts go straight to the
Layers tab.

## LayerInfo
Dataclass for one layer: `name`, viewport/render/lock/solo flags, `color`, and
the three reference counts `object_count` / `material_count` / `tag_count` plus
`poly_count`, and `all_object_count` (object count IGNORING the visibility
filter; `None` when the caller has no unfiltered counts). `empty` is a
property: **true only when nothing references the layer** — no objects AND no
materials AND no tags. It judges objects by `all_object_count` when available,
so a layer whose only objects are hidden never counts as empty under the
"Visible only" perspective (the delete offer would fail server-side).
`to_dict()` renders the JSON the frontend consumes (`objects` / `objects_all` /
`materials` / `tags` / `polys` / `empty`).

## build_layer_report(layer_meta, object_counts=None, poly_counts=None, no_layer=0, all_object_counts=None)
Assembles `{layers, no_layer, total_layers, empty_layers}`. `layer_meta` is the
per-layer metadata from the adapter's `scan_layers` (each dict carries
`materials` / `tags` counts via `c4d.ID_LAYER_LINK`); `object_counts` and
`poly_counts` come from the analyzer's per-layer aggregation (perspective-
filtered); `all_object_counts` is the adapter's unfiltered per-layer object
count and feeds only the `empty` judgement + `objects_all`. A layer present in
`object_counts` but missing from `layer_meta` is still listed. `empty_layers`
counts only truly-empty layers — the number the "Delete N empty" action removes.

## LayerMismatch / find_layer_mismatches(tree, keep=None)
An object whose assigned layer differs from its parent's assigned layer (both
non-empty). Reported as an **informational finding only** — a null on one layer
with its geometry on another is frequently deliberate, so this is never part of
an auto-apply. `keep` filters accepted names via the shared keeps mechanism
([core/keeps](keeps.md)); accepting one drops it from the list. `to_dict()`
carries `guid` / `name` / `path` / `parent` / `parent_layer` / `child_layer`.
