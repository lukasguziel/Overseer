from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Config
from ..naming.convention import NamingConvention
from ..structure.rules import RuleContext
from . import model, ops


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

    ctx = RuleContext(tree=tree, convention=conv, standard=cfg.standard,
                      scope=scope)
    bundle = cfg.rules.plan_all(ctx)
    plan.renames.extend(bundle.renames)
    plan.layers.extend(bundle.layers)
    plan.applied_rules.extend(bundle.applied_rules)
    plan.warnings.extend(bundle.warnings)
    renamed = {op.guid for op in bundle.renames}
    layered = {op.guid for op in bundle.layers}

    for op in ops.plan_renames(tree, conv, scope=scope, prefixes=cfg.prefixes):
        if op.guid not in renamed:
            plan.renames.append(op)
            renamed.add(op.guid)

    plan.reparents.extend(ops.plan_reparents(
        tree, cfg.standard, scope=scope, safe_only=safe_only, tidy=tidy))

    for op in ops.plan_layers(tree, scope=scope):
        if op.guid not in layered:
            plan.layers.append(op)
            layered.add(op.guid)

    return plan


def filter_accepted(plan: CombinedPlan, accept: dict | None) -> CombinedPlan:
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
