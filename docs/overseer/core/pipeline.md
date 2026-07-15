# core/pipeline

Combined one-click planning: rules + naming + structure + layers. Pure, no `c4d`. This is the engine behind the web API's `plan_all` / `apply_all`: one tree read produces every proposed change, merged deterministically:

1. Declarative rules (`overseer.structure.rules`) claim first, by priority.
2. Naming normalization for objects no rule renamed.
3. Structure reparents (safety filter + tidy semantics).
4. Layer rules first, then the default layer scheme for the rest.

## CombinedPlan
Dataclass of `renames`, `reparents`, `layers`, `applied_rules`, `warnings`.
- `total`: count of renames + reparents + layers.

## Functions
- `plan_combined(tree, cfg, convention=None, scope=None, safe_only=True, tidy=True)`: builds the merged plan. Uses `cfg.convention` unless overridden. Runs the rule set via `RuleContext`, then fills gaps with `ops.plan_renames` (skipping guids a rule already renamed), `ops.plan_reparents`, and `ops.plan_layers` (skipping guids a layer rule already claimed).
- `filter_accepted(plan, accept)`: restricts a plan to user-accepted guids per section. `accept = {"naming": [...], "structure": [...], "layers": [...]}`; a missing key means accept everything in that section. Returns a new `CombinedPlan` preserving `applied_rules` and `warnings`.
