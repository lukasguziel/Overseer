"""Scan folders recursively for scene reports (without reading them whole).

Usage: python scan_reports.py <folder> [<folder2> ...]
A JSON file is a report if it carries 'nodes' AND 'object_count'.
"""
import glob
import json
import sys

if len(sys.argv) < 2:
    sys.exit("usage: scan_reports.py <folder> [...]")

found = 0
for folder in sys.argv[1:]:
    for f in sorted(glob.glob(folder + "/**/*.json", recursive=True)):
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        if "nodes" in d and "object_count" in d:
            found += 1
            print("%s -> %s | %s obj | depth %s | %s" % (
                f, d.get("file"), d.get("object_count"),
                d.get("max_depth"), d.get("analyzed_at", "")))
print("-- %d report(s) found" % found)
