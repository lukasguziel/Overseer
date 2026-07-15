# core/tags_logic.py

Pure helpers for the tag audit — no `c4d`, unit-tested in CI. The c4d-bound
adapter collects the raw tag types and calls in here for the folding logic.

## `merge_selection_types(type_list, kind_by_type)`

Folds the point / polygon / edge selection tag types into ONE `"Selection"`
entry: each object appears once, its tags stamped with their selection `kind`
(`"point"` / `"polygon"` / `"edge"`), and the entry carries every source id in
`type_ids` so select-in-C4D can cover all three.

Entries look like `{type_id, label, count, objects:[{guid, name, tags:[{name,
kind?}]}]}`; non-selection entries pass through untouched. The result is
re-sorted by `(-count, label)`.

## Other helpers

- `deg_from_rad(rad)` — radians to degrees, rounded to one decimal (phong angle
  display).
- `dominant_angle(counts)` — the most common phong angle in a `{angle: count}`
  map, ties broken by the larger angle; `None` for an empty map.
