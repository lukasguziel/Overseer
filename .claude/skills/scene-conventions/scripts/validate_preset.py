"""Validate a preset v2 file against the real sceneorg config/rules logic.

Run from the repo root:
    python .claude/skills/scene-conventions/scripts/validate_preset.py src/presets/<id>.json

Checks: schema/meta present, settings load through sceneorg.config.load_config,
compile_rules produces no warnings, casing/language valid, structure tree well
formed (unique paths, known keys). Prints a human summary.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from sceneorg import config as C  # noqa: E402
from sceneorg import rules as R  # noqa: E402

PRODUCIBLE = {"PascalCase", "camelCase", "lower_snake", "UPPER_SNAKE", "kebab"}
STRUCT_KEYS = {"name", "categories", "keywords", "aliases", "priority",
               "children", "parent"}

if len(sys.argv) != 2:
    sys.exit("usage: validate_preset.py <preset.json>")

with open(sys.argv[1], encoding="utf-8") as f:
    p = json.load(f)

errors = []
warnings = []

if int(p.get("schema", 0)) != 2:
    errors.append("top-level schema must be 2 (got %r)" % p.get("schema"))

meta = p.get("meta", {})
for key in ("id", "name"):
    if not meta.get(key):
        errors.append("meta.%s missing" % key)

if "settings" not in p:
    errors.append("no 'settings' block (v2 presets snapshot the full config)")
settings = p.get("settings", {})

if settings.get("casing") not in PRODUCIBLE:
    errors.append("casing %r not producible (%s)"
                  % (settings.get("casing"), sorted(PRODUCIBLE)))
if settings.get("language") not in ("en", "de", None):
    errors.append("language must be en/de/null")


def walk_structure(nodes, path_prefix, seen):
    for g in nodes or []:
        if not g.get("name"):
            errors.append("structure group without name: %r" % g)
            continue
        unknown = set(g) - STRUCT_KEYS
        if unknown:
            warnings.append("structure %r: unknown keys %s"
                            % (g["name"], sorted(unknown)))
        full = ("%s/%s" % (path_prefix, g["name"])) if path_prefix else g["name"]
        if full in seen:
            errors.append("duplicate structure path %r" % full)
        seen.add(full)
        walk_structure(g.get("children"), full, seen)


walk_structure(settings.get("structure"), "", set())

# Rules: compile through the real engine, surface any warnings.
ruleset = R.compile_rules(settings.get("rules"))
for w in ruleset.warnings:
    errors.append("rule compile: %s" % w)

# Full load (also runs migrate_config + build_standard).
try:
    cfg = C.load_config(settings)
except Exception as ex:  # noqa: BLE001
    errors.append("load_config: %s" % ex)
    cfg = None

if errors:
    print("INVALID:")
    for e in errors:
        print(" -", e)
    for w in warnings:
        print(" (warn)", w)
    sys.exit(1)

print("preset valid:", meta.get("id"))
print("  casing=%s language=%s pad=%s"
      % (settings.get("casing"), settings.get("language"),
         settings.get("number_pad")))
print("  structure groups:", len(cfg.standard.rules) if cfg else "?",
      [r.path for r in cfg.standard.rules] if cfg else "")
print("  rules:", len(ruleset.rules),
      [(r.type, r.id) for r in ruleset.rules])
print("  translations:", len(settings.get("translations") or {}))
for w in warnings:
    print("  (warn)", w)
