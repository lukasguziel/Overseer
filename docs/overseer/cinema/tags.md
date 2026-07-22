# cinema/tags.py

[c4d] Tag audit: counts tag types across the scene, flags meshes missing a
Phong tag and objects carrying duplicate material tags, and can add/retune
Phong tags or strip duplicate material tags. Imports `c4d`; never loaded by the
unit tests. Runs on the C4D main thread.

## Module constants

- Tag type ids (`_TPHONG`, `_TTEXTURE`, …) and Phong parameter ids are resolved
  via `getattr` with fallback ids so the module imports even where a symbol is
  missing from a given C4D build.
- `_INTERNAL_TAG_TYPES` — point/polygon/tangent/segment/… tags that are
  geometry payload, not artist-facing; excluded from the audit.
- `_SELECTION_KINDS` — point/polygon/edge selection tag ids folded into ONE
  "Selection" entry; the kind travels on each object's tags via
  `merge_selection_types`.
- `_TAG_VISIBLE` — the `TAG_VISIBLE` info bit (see `_type_visible`).

## Functions

- `_type_visible(type_id, cache)` — whether this tag type shows up in the Object
  Manager. Data tags (per-geometry point/weight/… payloads) are registered
  without `TAG_VISIBLE`; auditing them only confuses, the artist can't see them.
  Unknown types count as visible: showing too much beats hiding real tags.
  Cached per type id because the plugin lookup is not free.
- `_tag_type_label(tag)` — readable label: `GetTypeName()` first, then
  `GetObjectName(GetType())`, else `Tag <id>`.
- `_has_phong(obj)` — whether the object carries a Phong tag.
- `_scan(...)` — single walk building the per-type counts, the per-object rows,
  duplicate material-tag findings, missing-Phong findings and the Phong-angle
  distribution. One row per OBJECT per type: every tag of that type lands in the
  row's tag list, so an object with three selection tags does not show up three
  times.
- `_add_phong(...)` — inserts a Phong tag on meshes that lack one, at the scene's
  dominant Phong angle (or `DEFAULT_PHONG_ANGLE_DEG` if none). One undo step.
- `_current_phong_angles` — angle histogram of existing Phong tags, feeding the
  dominant-angle default above.
- `_set_phong_angle(...)` — retunes the Phong angle on selected/all meshes. One
  undo step.
- `_delete_duplicates(...)` — removes redundant material tags (same material
  linked more than once on an object), keeping the first. One undo step.
- `_select(...)` — selects objects by `guids`, or by tag `type_id(s)`. A merged
  "Selection" entry sends `type_ids` (a list); single entries send one `type_id`.
- `handle(op, ...)` — dispatch for `tags_scan` / `tags_add_phong` /
  `tags_set_phong_angle` / `tags_delete_duplicates` / `tags_select`.

Angle math, selection-type merging and dominant-angle logic live in the pure
`core/tags_logic`.
