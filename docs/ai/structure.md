# overseer.structure — group standard + rule engine v2 + graph

Pure domain layer (no `c4d`) for scene structure: the group standard that maps
objects to canonical containers, the declarative rule engine v2 that plans
renames/layer assignments, and the node-editor graph serialization. Testable in
CI.

## Modules

### standard.py
`GroupRule` (match by category OR translated keyword, optional `parent` for
nesting, `aliases` for existing containers) + `StructureStandard`, whose
`evaluate()` walks a `SceneTree` and produces a `StructureReport` of `Finding`s
with a `compliance` ratio. `default_standard()` ships Cameras+Lights only.
Gotcha: `container_rule()` disambiguates same-named rules by the node's
enclosing group path, falling back to a parent-less rule then the first
candidate.

### rules.py
Declarative rule engine v2. `Rule(ABC)` with abstract `from_dict`/`to_dict`/
`plan` (`...` bodies); concrete subclasses `PrefixRule`, `RenumberRule`,
`ConditionRule`, `LayerRule` register in the `RULE_TYPES` registry.
`compile_rules()` turns raw dicts into a `RuleSet` (collecting warnings for
unknown/invalid entries), `RuleSet.plan_all()` runs rules by descending priority
into one `PlanBundle`. `Match` is the shared node-selection vocabulary; `RuleContext`
carries tree/convention/standard/scope. Gotcha: first rule to touch a node's
rename/layer wins (`renamed`/`layered` guard sets).

### graph.py
`graph_from_structure()` (nested, depth-aware) and `graph_from_groups()` (flat)
serialize group definitions into React-Flow `{nodes, edges}` for the web node
editor. Pure layout math; category/keyword nodes fan into their group node.

### __init__.py
Empty package marker.

## Conventions & gotchas
- Every `Rule` subclass MUST register in `RULE_TYPES` keyed by its `type` string;
  `compile_rules()` dispatches through it — an unregistered type is silently
  skipped with a warning.
- Prefer polymorphism (`rule.plan(ctx)`) over type-switching on `rule.type`.
- Rule-type name strings and `RULE_TYPES` keys are DATA, not comments.
- Nested structure is handled via `GroupRule.parent`/`path` and the graph's
  recursive `emit()`; `path_complies()` treats a node under a subgroup as
  compliant with the parent group.

Per-module prose: see the mirrored files under `docs/overseer/structure/`.
