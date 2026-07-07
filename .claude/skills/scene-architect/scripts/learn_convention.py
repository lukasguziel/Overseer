"""Konvention ueber mehrere Reports aggregieren (Casing/Sprache/Roots/Junk).

Aufruf: python learn_convention.py <report.json> [<report2.json> ...]
        python learn_convention.py reports/*.json
"""
import collections
import json
import re
import sys

JUNK = re.compile(r"^(cube|wuerfel|würfel|polygon|null|sphere|kugel|plane|ebene|"
                  r"cylinder|zylinder|licht|light|camera|kamera)([ ._-]?\d*)?$", re.I)

if len(sys.argv) < 2:
    sys.exit("usage: learn_convention.py <report.json> [...]")

cas = collections.Counter()
lang = collections.Counter()
roots = collections.Counter()
junk = collections.Counter()
dupes = collections.Counter()
total = 0

for f in sys.argv[1:]:
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    total += d.get("object_count", 0)
    for k, v in d.get("casing", {}).items():
        cas[k] += v
    for k, v in d.get("language", {}).items():
        lang[k] += v
    names = collections.Counter()
    for n in d.get("nodes", []):
        if n["depth"] == 0 and n["children"]:
            roots[n["name"]] += 1
        if JUNK.match(n["name"]):
            junk[JUNK.match(n["name"]).group(1).lower()] += 1
        names[n["name"]] += 1
    for name, c in names.items():
        if c > 3:
            dupes[name] += c

print("REPORTS  %d, Objekte gesamt %d" % (len(sys.argv) - 1, total))
print("CASING  ", cas.most_common(6))
print("LANG    ", lang.most_common())
print("ROOTS   ", roots.most_common(20))
print("JUNK    ", junk.most_common(10), "(Default-Namen -> Rename-Kandidaten)")
print("DUPES   ", dupes.most_common(10), "(Name >3x -> disambiguate/pruefen)")
