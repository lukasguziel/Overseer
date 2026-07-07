"""Offline simulation of the one-button apply.

Loads a preset v2 plus one or more reports, rebuilds a SceneTree from each
report's flat node list, runs sceneorg.pipeline.plan_combined, and prints the
op counts, a sample of each section, and the resulting structure compliance.
This is the "would the preset actually do the right thing" check before any
deploy/apply -- it needs no C4D.

Run from the repo root:
    python .claude/skills/scene-conventions/scripts/dry_run.py \
        src/presets/<id>.json reports/<scene>.json [<scene2>.json ...]

guid caveat: report guids are traversal indices for THAT export only. This
simulation is valid against the same report; never freeze the produced guid
plan for a later live apply (the live API re-plans server-side).
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from sceneorg import config as C  # noqa: E402
from sceneorg.core import model, pipeline  # noqa: E402

if len(sys.argv) < 3:
    sys.exit("usage: dry_run.py <preset.json> <report.json> [<report2.json> ...]")

with open(sys.argv[1], encoding="utf-8") as f:
    preset = json.load(f)
settings = preset.get("settings", preset)
cfg = C.load_config(settings)


def build_tree(report):
    """Flat preorder+depth node list -> SceneTree with parent/child links."""
    tree = model.SceneTree()
    stack = []   # (depth, SceneNode)
    for nd in report.get("nodes", []):
        node = model.SceneNode(
            name=nd.get("name", ""),
            type_name=nd.get("type", "Null"),
            category=nd.get("category", model.CAT_OTHER),
            guid=nd.get("guid", -1),
            point_count=nd.get("points", 0),
            poly_count=nd.get("polygons", 0),
        )
        depth = nd.get("depth", 0)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        if stack:
            stack[-1][1].add_child(node)
        else:
            tree.roots.append(node)
        stack.append((depth, node))
    return tree


def sample(items, fmt, n=8):
    for it in items[:n]:
        print("     ", fmt(it))
    if len(items) > n:
        print("      ... +%d more" % (len(items) - n))


for report_path in sys.argv[2:]:
    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)
    tree = build_tree(report)
    before = cfg.standard.evaluate(tree)
    plan = pipeline.plan_combined(tree, cfg)

    print("=" * 70)
    print("PRESET %s   x   REPORT %s (%s objs)"
          % (preset.get("meta", {}).get("id", "?"),
             os.path.basename(report_path), report.get("object_count")))
    print("  compliance before: %.2f" % before.compliance)
    print("  renames:   %d" % len(plan.renames))
    sample(plan.renames, lambda r: "%s -> %s" % (r.old_name, r.new_name))
    print("  reparents: %d" % len(plan.reparents))
    sample(plan.reparents, lambda r: "%s: %s -> %s"
           % (r.name, r.from_group, r.to_group))
    print("  layers:    %d" % len(plan.layers))
    sample(plan.layers, lambda o: "%s -> [%s]" % (o.name, o.layer))
    print("  rules applied:", plan.applied_rules)
    if plan.warnings:
        print("  warnings:")
        sample(plan.warnings, lambda w: w)
    print("  total ops: %d" % plan.total)
