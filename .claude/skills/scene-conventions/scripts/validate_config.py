# Validate a config.json (v1 or v2) without C4D: load it through
# sceneorg.config (which migrates v1 -> v2), show convention + structure +
# compiled rules, and test canonical_group() against real container names.
# Usage: python validate_config.py [config.json] [ContainerName ...]
import json
import os
import sys

cfg_path = sys.argv[1] if len(sys.argv) > 1 else "src/config.json"
names = sys.argv[2:]

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                "..", "..", "..", "..", "src"))
from sceneorg import config as C  # noqa: E402
from sceneorg.naming import translations as T  # noqa: E402

data = json.load(open(cfg_path, encoding="utf-8"))
T.add_translations(data.get("translations", {}))
cfg = C.load_config(data)

print("schema", data.get("schema", 1), "(migrated to 2 on load)")
print("OK", cfg.convention.style.value, cfg.convention.language,
      "pad", cfg.convention.number_pad)
print("structure", [r.path for r in cfg.standard.rules])
print("rules", [(r.type, r.id) for r in cfg.rules.rules])
if cfg.rules.warnings:
    print("rule warnings:", cfg.rules.warnings)
for nm in names:
    print(nm, "->", cfg.standard.canonical_group(nm))
if not names:
    print("(tip: pass real container names as arguments"
          " to test alias detection)")
