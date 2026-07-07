"""Preset-Datei gegen die echte sceneorg-Config-Logik validieren.

Aufruf (aus dem Repo-Root): python .claude/skills/scene-architect/scripts/validate_preset.py src/presets/<id>.json
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "src"))
from sceneorg import config as C  # noqa: E402
from sceneorg import graph as G  # noqa: E402

if len(sys.argv) != 2:
    sys.exit("usage: validate_preset.py <preset.json>")

with open(sys.argv[1], encoding="utf-8") as f:
    p = json.load(f)

errors = []
meta = p.get("meta", {})
if not meta.get("id"):
    errors.append("meta.id fehlt")
PRODUCIBLE = {"PascalCase", "camelCase", "lower_snake", "UPPER_SNAKE", "kebab"}
if p.get("casing") not in PRODUCIBLE:
    errors.append("casing '%s' nicht producible (%s)" % (p.get("casing"), sorted(PRODUCIBLE)))
if p.get("language") not in ("en", "de", None):
    errors.append("language muss en/de/null sein")
for g in p.get("groups", []):
    if not g.get("name"):
        errors.append("group ohne name: %r" % g)

cfg = {k: p[k] for k in ("casing", "language", "number_pad", "prefixes",
                         "translations", "groups") if k in p}
cfg["graph"] = G.graph_from_groups(p.get("groups", []))
try:
    C.load_config(cfg)
except Exception as ex:
    errors.append("load_config: %s" % ex)

if errors:
    print("INVALID:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("preset valid: %s (%d groups, %d translations)" % (
    meta.get("id"), len(p.get("groups", [])), len(p.get("translations", {}))))
