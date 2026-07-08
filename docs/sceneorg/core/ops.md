# core/ops

Change operations as pure data objects plus planners. No `c4d`. The adapter later executes these operations in the document with undo support.

## Operation dataclasses
- `RenameOp(guid, old_name, new_name)`
- `ReparentOp(guid, name, from_group, to_group)`
- `LayerOp(guid, name, layer)`

## DEFAULT_LAYER_SCHEME
The type axis ("what is it") belongs in layers, NOT in the null hierarchy (which carries the spatial axis). This lets everything of one type be toggled/rendered without flattening the spatial structure. Maps category (Light->Lights, Camera->Cameras) or type_name (Instance->Proxies) to a layer name.

## Functions
- `layer_for(node, scheme=None)`: layer name for an object per scheme (type match wins over category), or `None`.
- `is_safe_to_reparent(node)`: only move if the object is parented purely for organization. Children of generators/deformers/meshes (Cloner, Boole, Sweep, ...) must NOT be moved — that would change the render result. Heuristic: safe only if the parent is the root or a null.
- `plan_renames(tree, convention, scope=None, prefixes=None)`: renames for non-conforming objects, collision-safe per parent. `scope` limits which guids to rename (None = all); siblings not being renamed reserve their names. `prefixes` maps `{category: prefix}` (e.g. `{'light': 'LGT_'}`) and is idempotent — an existing prefix is stripped before normalizing and re-added. Disambiguates against used names.
- `plan_reparents(tree, standard, scope=None, safe_only=True, tidy=True)`: regroupings for misplaced objects with a safety filter. `tidy=True` (default, safe) collects ONLY truly loose objects that sit in NO recognized group; objects already inside a (possibly nested) group container are left alone, preserving a well-thought-out spatial hierarchy. `tidy=False` is aggressive — also moves objects out of a wrong group to the root-level target (can tear apart the structure).
- `plan_layers(tree, scope=None, scheme=None)`: layer assignments per scheme (type axis) without changing the hierarchy.
