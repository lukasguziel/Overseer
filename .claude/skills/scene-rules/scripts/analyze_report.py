# Aggregiert scene_report.json (1-2 MB) fuer den Kontext: Kennzahlen,
# Root-Taxonomie, Token-Frequenzen und noch unuebersetzte deutsche Tokens.
# Usage: python analyze_report.py [report.json]
import collections
import json
import os
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("var", "scene_report.json")
d = json.load(open(path, encoding="utf-8"))

print("file", d["file"])
print("objs", d["object_count"], "depth", d["max_depth"],
      "compliance", d["structure_compliance"])
print("types", d["types"])
print("categories", d["categories"])
print("casing", d["casing"])
print("language", d["language"])

print("\n-- Root-Taxonomie (depth<=2, Container) --")
for x in d["nodes"]:
    if x["depth"] <= 2 and x["children"]:
        print("  " * x["depth"] + x["name"] + " <%d>" % x["children"])

tok = collections.Counter()
for x in d["nodes"]:
    for t in re.findall(r"[A-Za-zÄÖÜäöüß]+", x["name"]):
        if len(t) > 2:
            tok[t.lower()] += 1
print("\n-- Tokens (Top 60) --")
print(tok.most_common(60))

# Welche Tokens kennt der eingebaute Wortschatz noch nicht?
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "src"))
try:
    from sceneorg.naming import translations as T
    known = T.DE_WORDS | {w.lower() for w in T.EN_WORDS}
    unknown = [(w, n) for w, n in tok.most_common()
               if w not in known and (not w.isascii() or n >= 3)]
    print("\n-- Tokens ohne Uebersetzung (Kandidaten fuer config translations) --")
    print(unknown[:40])
except Exception as e:  # noqa: BLE001 - nur Diagnose
    print("(sceneorg nicht importierbar:", e, ")")
