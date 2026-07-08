# structure/graph.py

Generates the node-editor layout from group rules (pure, no c4d). The Rules tab (`RuleGraph.jsx`) renders ONLY from a stored `graph` (nodes/edges). Presets and the skill however only provide `groups`/`structure`, so these functions build the matching layout so a loaded preset shows up in the editor immediately.

## Public functions

- **`graph_from_structure(structure) -> dict`** — Builds `{nodes, edges}` from a NESTED structure tree (config schema 2). Child groups connect to their parent group via a group->group edge; the editor reads that edge back as the `parent` relation. Depth shifts the x position (`520 + depth * 260`) so nesting is visible at a glance. Recurses over each group's `children`. IDs follow the `<type>_<n>` scheme.

- **`graph_from_groups(groups) -> dict`** — Builds `{nodes, edges}` for React Flow from a flat list of groups. One group node per group (right, x=520); one category node per category and one keyword node per keyword set (left), connected via edges. IDs follow the `<type>_<n>` scheme the editor expects when re-counting.
