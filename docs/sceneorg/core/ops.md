# core/ops

Change operations as an OOP hierarchy plus planners. No `c4d`. The adapter later executes these operations in the document with undo support.

## Interfaces (ABCs)
- `Writer` — the abstract sink an operation writes to: `rename(node, new_name)`, `reparent(node, to_group)`, `assign_layer(node, layer)`. Pure code (and tests) implement it; the c4d `SceneAdapter` consumes the same op fields through its batched, single-undo apply methods.
- `Operation` — abstract base for every change op. Holds a live `node: SceneNode` reference (data is linked, not copied): `guid` and `name` are read-through properties of `node`. Each op implements `apply(writer)` (polymorphic dispatch) and `to_dict()`.

## Operation classes (link back to their SceneNode)
- `RenameOp(node, new_name)` — `old_name` is `node.name`; `apply` → `writer.rename`.
- `ReparentOp(node, to_group, from_group)` — `apply` → `writer.reparent`.
- `LayerOp(node, layer)` — `apply` → `writer.assign_layer`.

The `node` field is `compare=False` so op equality ignores the (self-referential) node graph and never recurses.

## DEFAULT_LAYER_SCHEME
Imported from [core/defaults](defaults.md). The type axis ("what is it") belongs in layers, NOT in the null hierarchy (which carries the spatial axis). This lets everything of one type be toggled/rendered without flattening the spatial structure. Maps category (Light->Lights, Camera->Cameras) or type_name (Instance->Proxies) to a layer name.

## Functions
- `layer_for(node, scheme=None)`: layer name for an object per scheme (type match wins over category), or `None`.
- `is_safe_to_reparent(node)`: only move if the object is parented purely for organization. Children of generators/deformers/meshes (Cloner, Boole, Sweep, ...) must NOT be moved — that would change the render result. Heuristic: safe only if the parent is the root or a null.
- `plan_renames(tree, convention, scope=None, prefixes=None)`: renames for non-conforming objects, collision-safe per parent. `scope` limits which guids to rename (None = all); siblings not being renamed reserve their names. `prefixes` maps `{category: prefix}` (e.g. `{'light': 'LGT_'}`) and is idempotent — an existing prefix is stripped before normalizing and re-added. Disambiguates against used names.
- `plan_reparents(tree, standard, scope=None, safe_only=True, tidy=True)`: regroupings for misplaced objects with a safety filter. `tidy=True` (default, safe) collects ONLY truly loose objects that sit in NO recognized group; objects already inside a (possibly nested) group container are left alone, preserving a well-thought-out spatial hierarchy. `tidy=False` is aggressive — also moves objects out of a wrong group to the root-level target (can tear apart the structure).
- `plan_layers(tree, scope=None, scheme=None)`: layer assignments per scheme (type axis) without changing the hierarchy.
- `plan_layer_suggestions(tree, scope=None, keep=None)`: for objects with NO layer, propose the nearest ancestor's layer (inherit down the hierarchy). Returns `LayerOp`s rendered as accept/reject rows in the no-layer worklist. Objects with no layered ancestor, out-of-scope objects, and kept names produce no suggestion.
