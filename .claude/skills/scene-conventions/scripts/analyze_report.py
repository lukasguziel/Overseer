# Aggregates a single scene_report.json (1-2 MB) for the context: key numbers,
# root taxonomy, token frequencies and still-untranslated German tokens.
# Usage: python analyze_report.py [report.json]
import collections
import json
import os
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "scene_report.json"
d = json.load(open(path, encoding="utf-8"))

print("file", d.get("file"))
print("objs", d.get("object_count"), "depth", d.get("max_depth"),
      "compliance", d.get("structure_compliance"))
print("types", d.get("types"))
print("categories", d.get("categories"))
print("casing", d.get("casing"))
print("language", d.get("language"))

print("\n-- Root taxonomy (depth<=2, containers) --")
for x in d.get("nodes", []):
    if x.get("depth", 0) <= 2 and x.get("children"):
        print("  " * x["depth"] + x["name"] + " <%d>" % x["children"])

tok = collections.Counter()
for x in d.get("nodes", []):
    # [^\W\d_] = any unicode letter (umlauts included), no ASCII literals.
    for t in re.findall(r"[^\W\d_]+", x["name"], re.UNICODE):
        if len(t) > 2:
            tok[t.lower()] += 1
print("\n-- Tokens (Top 60) --")
print(tok.most_common(60))

# Which tokens does the built-in vocabulary not know yet?
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
try:
    from sceneorg import translations as T
    known = T.DE_WORDS | {w.lower() for w in T.EN_WORDS}
    unknown = [(w, n) for w, n in tok.most_common()
               if w not in known and (not w.isascii() or n >= 3)]
    print("\n-- Tokens without translation (candidates for config translations) --")
    print(unknown[:40])
except Exception as e:  # noqa: BLE001 - diagnostic only
    print("(sceneorg not importable:", e, ")")
