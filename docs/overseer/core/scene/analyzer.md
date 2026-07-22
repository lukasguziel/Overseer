# core/analyzer

SceneAnalyzer aggregates a `SceneTree` into a `SceneReport` in a single pass. Pure domain logic, never imports `c4d`.

## SceneReport
Dataclass holding all aggregated dashboard statistics: object/point/poly counts, per-type/category/casing/language distributions, top-level nodes, poly rankings, light/camera group breakdowns, and per-node dicts.

- `hidden_count`: objects hidden in the Object Manager across the whole tree.
- Layer usage fields (`layers_by_name`, `polys_by_layer`, `no_layer_count`): map layer name to object count / polygons, plus a "no layer" bucket. Layer metadata (color/flags/empty layers) is merged in later by the c4d adapter (webapi), which alone can read the document's layer table.
- `to_dict()`: JSON-friendly serialization.

## SceneAnalyzer
- `analyze(tree, file_name="", scope=None, include_hidden=True)`: single pass over `tree.walk()` computing every statistic; casing/language detected once per object.
  - `scope` (guid set) restricts ALL stats to the selection subtree, so every dashboard number reflects the selection.
  - `include_hidden=False` drops objects hidden in the Object Manager (editor dot OFF, inherited) from EVERY statistic — counts, polys, casing and asset list alike — so numbers reflect only what is visible.
  - Any active filter (scope or hidden-excluded) makes `top_level` follow the filtered node set instead of the raw roots; a filtered compliance is recomputed from the scoped correct/misplaced counts.
