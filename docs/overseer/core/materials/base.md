# core/materials/logic.py

Pure helpers for the material audit — no `c4d`, unit-tested in CI.

## `is_internal_material(name)`

`True` for a renderer plugin's internal helper material — e.g. Octane's
`__octanetemp__` clipboard/preview material. These look unused to the scan but
belong to the plugin: never list them as unused, never delete them. The dunder
naming (`__...__`) is the convention those helpers share, so any material whose
name is longer than four characters and both starts and ends with `__` is
treated as internal.
