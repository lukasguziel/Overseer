# core/defaults

Central home for the plugin's built-in domain constants. Pure (no `c4d`), so
every layer/category default lives in one place instead of being scattered
across modules. c4d-bound tables (object-type ids) live in
[cinema/constants](../cinema/constants.md) instead, because they must import
`c4d`.

## Constants
- `RS_LIGHT_IDS`, `RS_CAMERA_IDS` — Redshift light/camera plugin type ids, used by the adapter's `classify()` so Redshift objects are categorized as light/camera.
- `CATEGORY_LAYERS` — category → layer name (`light`→`Lights`, `camera`→`Cameras`).
- `TYPE_LAYERS` — type name → layer name (`Instance`→`Proxies`).
- `DEFAULT_LAYER_SCHEME` — `{categories, types}` view built from the two maps above; consumed by `core/ops.layer_for` / `plan_layers`.
- `LAYER_COLORS` — layer name → RGB (0..1) tuple for the auto-created type layers; consumed by the adapter when it creates a layer.
