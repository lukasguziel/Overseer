# structure/standard.py

Structure standard: expected top-level (and nested) groups plus evaluation of a scene against them (pure, no c4d).

## Classes

- **`GroupRule`** — A target group (null container) and how objects are assigned to it. Fields: `name`, `match_categories` (object categories that belong here), `match_keywords` (English name tokens that route here), `aliases` (alternative container names, e.g. `Moebel` == `Furniture`), `priority` (higher wins when several rules match), `parent` (parent group path, None = top-level). `path` yields the full group path (`Room/Furniture`). `matches(node)` is true on a category hit or when translated name tokens intersect the keywords (language-independent).

- **`Finding`** — Per-object evaluation record: `guid`, `name`, `category`, `current_group`, `expected_group`, `misplaced`.

- **`StructureReport`** — Collection of `findings` plus `known_groups`. Properties: `misplaced`, `correct`, and `compliance` (fraction correct; 1.0 when empty).

- **`StructureStandard`** — Rule set for the desired scene organization. Rules are sorted priority-descending so specific rules apply first; internal maps resolve alias/name (lowercased) to a canonical group name and to all rules bearing that name.
  - `group_names` / `group_paths` — names and full paths of the rules.
  - `canonical_group(name)` — maps an actual container name to its canonical group name.
  - `container_rule(node)` — the rule a container null represents, parent-chain aware. When several rules share a name (e.g. `Lights` under `Room` vs under `Studio`), the one whose parent path matches the container's enclosing group wins; a top-level rule matches anywhere.
  - `target_group_for(node)` — target group PATH for an object, or None.
  - `is_group_container(node)` — is this null itself a recognized group container? NOT restricted to the root: groups may be nested at any level.
  - `enclosing_group(node)` — canonical name of the nearest recognized ancestor container, or None if the object is loose relative to the rules. Core of the hierarchy-aware evaluation (a light in `Scene > Lights > Interior` counts, even if the root is called `Scene`).
  - `enclosing_group_path(node)` — like `enclosing_group` but returns the rule's full path so nested standards evaluate correctly.
  - `path_complies(enclosing, expected)` (static) — a node complies if it sits in the expected group or deeper below it (a light under `Lights/Interior` still counts for `Lights`).
  - `evaluate(tree)` — single pass producing a `StructureReport`; skips group containers and objects with no expected group.

## Public functions

- **`default_standard() -> StructureStandard`** — Minimal, always-valid default with category-based rules only (Cameras, Lights). Cameras/Lights are unambiguous via object category and therefore always correct. Content groups (Furniture/Interior/Exterior etc.) are NOT guessed — they come from `config.json` or the node editor, tailored to the scene.
