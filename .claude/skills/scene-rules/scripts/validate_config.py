# Validiert src/config.json ohne C4D: laedt sie durch sceneorg.config,
# zeigt Konvention + Gruppen und testet canonical_group() gegen reale
# Container-Namen der Szene.
# Usage: python validate_config.py [config.json] [ContainerName ...]
import json
import os
import sys

cfg_path = sys.argv[1] if len(sys.argv) > 1 else "src/config.json"
names = sys.argv[2:]

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
from sceneorg import config as C  # noqa: E402
from sceneorg.naming import translations as T  # noqa: E402

data = json.load(open(cfg_path, encoding="utf-8"))
T.add_translations(data.get("translations", {}))
cfg = C.load_config(data)

print("OK", cfg.convention.style.value, cfg.convention.language,
      "pad", cfg.convention.number_pad)
print("groups", [r.name for r in cfg.standard.rules])
for nm in names:
    print(nm, "->", cfg.standard.canonical_group(nm))
if not names:
    print("(Tipp: reale Container-Namen als Argumente uebergeben,"
          " um Alias-Erkennung zu testen)")
