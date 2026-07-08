# core/model

Pure data model of the scene hierarchy. No `c4d`.

Category constants are deliberately strings (JSON-friendly): `CAT_LIGHT`, `CAT_CAMERA`, `CAT_NULL`, `CAT_MESH`, `CAT_SPLINE`, `CAT_OTHER`, plus the `ALL_CATEGORIES` tuple.

## SceneNode
One scene object, decoupled from `c4d.BaseObject`. `guid` is a stable index through which the adapter maps the real c4d object to write changes back.

Fields include `name`, `type_name`, `category`, `guid`, `depth`, `point_count` / `poly_count` (own + cache), `visible` (effective Object Manager visibility including ancestor inheritance — hidden if any ancestor is OFF), `layer` (assigned C4D layer name, `None` = no layer), plus `parent`/`children`.

- `subtree_polys` / `subtree_points`: aggregate over this node plus all descendants.
- `add_child(child)`: sets parent and depth, appends, returns the child.
- `walk()`: preorder over this node and all descendants.
- `descendants()`: like walk but excludes self.
- `ancestors()`: yields parents up to the root.
- `top_group()`: topmost ancestor (top-level node).
- `path`: "/"-joined name path from root.
- `child_count`: number of direct children.

## SceneTree
Wrapper around the root nodes (a document has multiple top-level objects).
- `walk()`: preorder over all roots.
- `all_nodes()`: list of all nodes.
- `by_category(category)`: nodes matching a category.
- `find(guid)`: node with the given guid, or `None`.
