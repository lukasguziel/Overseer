"""Plan-Datei statisch validieren, optional gegen einen Report.

Aufruf: python validate_plan.py <plan.json> [<report.json>]
Prueft: op-Typen, Pflichtfelder, $id vor Verwendung definiert, guids im Report
vorhanden (falls Report angegeben) — und gibt eine lesbare Vorschau aus.
"""
import json
import sys

if len(sys.argv) < 2:
    sys.exit("usage: validate_plan.py <plan.json> [<report.json>]")

with open(sys.argv[1], encoding="utf-8") as f:
    plan = json.load(f)

nodes = {}
if len(sys.argv) > 2:
    with open(sys.argv[2], encoding="utf-8") as f:
        rep = json.load(f)
    nodes = {n["guid"]: n for n in rep.get("nodes", [])}
    if plan.get("meta", {}).get("scene") and rep.get("file") \
            and plan["meta"]["scene"] != rep["file"]:
        print("WARN: plan.meta.scene=%r != report.file=%r" % (
            plan["meta"]["scene"], rep["file"]))

OPS = {"group", "rename", "move", "layer"}
errors = []
defined = set()


def check_ref(i, field, ref, required):
    if ref is None:
        if required:
            errors.append("#%d: %s fehlt" % (i, field))
        return
    if isinstance(ref, str):
        if not ref.startswith("$"):
            errors.append("#%d: %s=%r ist str aber kein $id" % (i, field, ref))
        elif ref not in defined:
            errors.append("#%d: %s=%r vor Definition verwendet" % (i, field, ref))
    elif nodes and ref not in nodes:
        errors.append("#%d: %s guid %s nicht im Report" % (i, field, ref))


def label(ref):
    if isinstance(ref, str):
        return ref
    n = nodes.get(ref)
    return "%s [%s]" % (n["path"], ref) if n else "guid %s" % ref


for i, op in enumerate(plan.get("operations", [])):
    kind = op.get("op")
    if kind not in OPS:
        errors.append("#%d: unbekannte op %r" % (i, kind))
        continue
    if kind == "group":
        check_ref(i, "under", op.get("under"), required=False)
        if op.get("id"):
            defined.add(op["id"])
        print("#%2d group  %-30s under %s" % (i, op.get("name", "GROUP"),
                                              label(op.get("under")) if op.get("under") is not None else "<root>"))
    elif kind == "rename":
        check_ref(i, "target", op.get("target"), required=True)
        print("#%2d rename %s -> %s" % (i, label(op.get("target")), op.get("to")))
    elif kind == "move":
        check_ref(i, "target", op.get("target"), required=True)
        check_ref(i, "into", op.get("into"), required=False)
        print("#%2d move   %s -> %s" % (i, label(op.get("target")),
                                        label(op.get("into")) if op.get("into") is not None else "<root>"))
    elif kind == "layer":
        check_ref(i, "target", op.get("target"), required=True)
        print("#%2d layer  %s -> %s" % (i, label(op.get("target")), op.get("layer")))

if errors:
    print("\nINVALID (%d):" % len(errors))
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("\nplan valid: %d operations%s" % (len(plan.get("operations", [])),
      "" if nodes else " (ohne Report geprueft — guids ungecheckt)"))
