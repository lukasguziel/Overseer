"""Combined one-click planning: rules + naming + structure + layers (pure).

This is the engine behind the web API's `plan_all`/`apply_all`: one tree
read produces every proposed change, merged deterministically:

  1. declarative rules (sceneorg.rules) claim first, by priority
  2. naming normalization for objects no rule renamed
  3. structure reparents (safety filter + tidy semantics)
  4. layer rules first, then the default layer scheme for the rest
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import model, ops
from .config import Config
from .convention import NamingConvention
from .rules import RuleContext


@dataclass
class CombinedPlan:
    renames: list = field(default_factory=list)
    reparents: list = field(default_factory=list)
    layers: list = field(default_factory=list)
    applied_rules: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.renames) + len(self.reparents) + len(self.layers)


def plan_combined(
    tree: model.SceneTree,
    cfg: Config,
    convention: NamingConvention | None = None,
    scope: set | None = None,
    safe_only: bool = True,
    tidy: bool = True,
) -> CombinedPlan:
    conv = convention or cfg.convention
    plan = CombinedPlan()

    # 1. Declarative rules claim first (priority order inside plan_all).
    ctx = RuleContext(tree=tree, convention=conv, standard=cfg.standard,
                      scope=scope)
    bundle = cfg.rules.plan_all(ctx)
    plan.renames.extend(bundle.renames)
    plan.layers.extend(bundle.layers)
    plan.applied_rules.extend(bundle.applied_rules)
    plan.warnings.extend(bundle.warnings)
    renamed = {op.guid for op in bundle.renames}
    layered = {op.guid for op in bundle.layers}

    # 2. Naming normalization for everything the rules did not touch.
    for op in ops.plan_renames(tree, conv, scope=scope, prefixes=cfg.prefixes):
        if op.guid not in renamed:
            plan.renames.append(op)
            renamed.add(op.guid)

    # 3. Structure (path targets, safety filter).
    plan.reparents.extend(ops.plan_reparents(
        tree, cfg.standard, scope=scope, safe_only=safe_only, tidy=tidy))

    # 4. Default layer scheme for objects no layer rule claimed.
    for op in ops.plan_layers(tree, scope=scope):
        if op.guid not in layered:
            plan.layers.append(op)
            layered.add(op.guid)

    return plan


def filter_accepted(plan: CombinedPlan, accept: dict | None) -> CombinedPlan:
    """Restrict a plan to user-accepted guids per section.

    accept = {"naming": [guids], "structure": [...], "layers": [...]};
    a missing key means 'accept everything in that section'.
    """
    if not accept:
        return plan

    def pick(items, key):
        if key not in accept:
            return list(items)
        allowed = set(accept[key] or [])
        return [op for op in items if op.guid in allowed]

    return CombinedPlan(
        renames=pick(plan.renames, "naming"),
        reparents=pick(plan.reparents, "structure"),
        layers=pick(plan.layers, "layers"),
        applied_rules=list(plan.applied_rules),
        warnings=list(plan.warnings),
    )
