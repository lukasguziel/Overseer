# structure/rules.py

Declarative, versioned rule engine (pure, no c4d). Rules live in `config.json` / presets as a list of dicts discriminated by `type` and compile into Rule objects that plan `RenameOp`/`LayerOp` via the existing planners' vocabulary. Unknown rule types are collected as warnings instead of crashing (forward compatibility: newer presets keep working on older plugins, minus the unknown rules). `RULES_SCHEMA_VERSION = 2`.

Rule types (`RULE_TYPES`):
- `prefix` — contextual prefixes, e.g. `LGT_` only for lights under `Studio`.
- `renumber` — gap renumbering, e.g. 1,2,3,6,7,9 -> 1..6 with padding.
- `condition` — declarative if/then, e.g. if >3 duplicates -> alpha suffixes.
- `layer` — layer assignment by match (extends the fixed default layer scheme).

Note: `_SUFFIX_SEP` mirrors `convention._NUM_SEP` (kept local because that dict is module-private). It is the separator between a base name and an appended number/letter suffix, keyed by casing.

## Classes

- **`RuleContext`** — Everything a rule may inspect while planning: `tree`, `convention`, `standard`, optional `scope` (set of guids). `in_scope(node)` is true when no scope is set or the node's guid is in scope.

- **`Match`** — Shared condition vocabulary for all rule types (extensible): `categories` (object categories), `keywords` (English name tokens; object tokens are translated first), `name_regex` (tested against the raw name; invalid regex fails closed), `under_group` (group path prefix resolved via the structure standard), `types` (C4D type names). `from_dict`/`to_dict` round-trip; `matches(node, ctx)` ANDs all set conditions.

- **`PlanBundle`** — Combined result of `RuleSet.plan_all()`: `renames`, `layers`, `applied_rules` (rule ids that produced ops), `warnings`.

- **`PrefixRule`** — Prepends `prefix` to every matching object name. Idempotent: names already carrying the prefix are left alone. Replaces/extends the flat per-category `prefixes` config of v1.

- **`RenumberRule`** — Reassigns trailing numbers as a gapless series. Matching numbered siblings sharing the same base name form a series, renumbered `start..n` in document (walk) order with `pad` zeros. Idempotent; unnumbered objects are never touched. `per_parent=True` (default) renumbers each sibling series independently; `False` renumbers one scene-wide series per base name. Skips (with a warning) a target name already taken by a non-renamed sibling.

- **`ConditionRule`** — Declarative if/then. `when`: `duplicates_gt N` (names occurring more than N times per parent) and/or `match` (restrict candidates). `then` (one action): `suffix_scheme` `alpha`|`numeric` (disambiguate duplicates with A/B/C or 01/02/03), `apply_prefix` (idempotent prefix), or `assign_layer` (put candidates on a layer). Unknown action -> warning. `_alpha` is spreadsheet-style (0->A, 25->Z, 26->AA).

- **`LayerRule`** — Assigns matching objects to a named layer (type axis, no hierarchy change).

- **`RuleSet`** — Holds compiled `rules` and compilation `warnings`. `plan_all(ctx)` runs all enabled rules priority-descending and merges ops with first-claim-wins semantics: later rules never re-rename or re-layer an object an earlier rule already claimed (deterministic, no op chains on stale names). `to_list()` serializes rules.

## Public functions

- **`compile_rules(raw) -> RuleSet`** — Turns `list[dict]` into a `RuleSet`. Unknown rule types and invalid rules (KeyError/TypeError/ValueError) become warnings and are skipped. Missing rule ids are auto-assigned as `<type>_<n>`.
