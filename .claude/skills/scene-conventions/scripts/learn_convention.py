"""Deep convention learning across one or more reports (never reads a report
into the model context -- it aggregates and prints compact stats + suggested
RuleV2 dicts).

Usage: python learn_convention.py <report.json> [<report2.json> ...]
       python learn_convention.py --json out.json reports/*.json

Sections:
  CASING / LANG        distribution over all names (+ per category)
  ROOTS                recurring top-level containers (= personal taxonomy)
  JUNK / DUPES         default-name and duplicate candidates
  NUMBERING            per sibling-series: gaps, padding distribution, start
                       index, per-parent vs global series
  AFFIXES              recurring prefixes AND suffixes (any casing, any
                       separator: 'ABC_', 'spl-', 'Geo.') correlated with four
                       axes -- category, type, parent container, root ancestor.
                       For each candidate: coverage (share of the axis members
                       that carry it), precision (share of affix carriers
                       inside the axis), counterexamples (members WITHOUT the
                       affix = what the rule would rename) and intruders
                       (carriers OUTSIDE the axis = why the match may be too
                       broad).
  SEMANTIC CLUSTERS    token co-occurrence within containers -> group-rule
                       candidates
  SUGGESTED RULES      JSON that maps directly onto RuleV2 / structure dicts;
                       suffix conventions land under "unsupported" (the engine
                       has no suffix rule yet -- report, don't enforce)

The suggestions are candidates, not decisions -- the interview phase confirms
them (see references/interview-guide.md).
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__),
                                "..", "..", "..", "..", "src"))
try:
    from sceneorg.naming import casing as naming
    from sceneorg.naming import translations
except Exception as exc:  # noqa: BLE001 - fall back to a lighter mode
    naming = None
    translations = None
    print("(sceneorg not importable, running without tokenizer:", exc, ")")

JUNK = re.compile(r"^(cube|wuerfel|null|sphere|kugel|plane|ebene|"
                  r"cylinder|zylinder|licht|light|camera|kamera|"
                  r"polygon|spline|boole|figur|figure)([ ._-]?\d*)?$", re.I)
# Leading/trailing affix: a short letter token plus an explicit separator.
# Any casing counts ('ABC_', 'spl-', 'Geo.'); the separator is part of the
# affix so the suggested prefix reproduces the user's exact style.
AFFIX_PRE = re.compile(r"^([A-Za-z]{1,8}[_\-.])(?=\S)")
AFFIX_SUF = re.compile(r"(?<=\S)([_\-.][A-Za-z]{1,8})$")
# Trailing number with its literal digits (to measure zero padding).
TRAILING = re.compile(r"^(.*?)[ _-]?(\d+)$")

# Affix candidate thresholds (tuned for interior scenes, 100-10k objects).
MIN_AFFIX_COUNT = 3      # affix must recur at least this often overall
MIN_AXIS_MEMBERS = 5     # axis value needs enough members to be a convention
MIN_COVERAGE = 0.55      # >= this share of the axis members carry the affix
MIN_PRECISION = 0.65     # >= this share of the carriers sit inside the axis

AXES = ("category", "type", "parent", "root")

args = sys.argv[1:]
json_out = None
if args[:1] == ["--json"]:
    if len(args) < 3:
        sys.exit("usage: learn_convention.py [--json out.json] <report.json> [...]")
    json_out = args[1]
    args = args[2:]
if not args:
    sys.exit("usage: learn_convention.py [--json out.json] <report.json> [...]")


def build_tree(report):
    """Rebuild parent/child links from the flat preorder+depth node list.

    Returns a list of (node_dict, parent_dict_or_None, root_dict_or_None).
    Report nodes stay plain dicts -- we only need name/depth/category/type.
    """
    linked = []
    stack = []   # (depth, node_dict)
    for nd in report.get("nodes", []):
        depth = nd.get("depth", 0)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1] if stack else None
        root = stack[0][1] if stack else None
        linked.append((nd, parent, root))
        stack.append((depth, nd))
    return linked


def english_tokens(name):
    if naming is None:
        return [t.lower() for t in re.findall(r"[^\W\d_]+", name, re.UNICODE)]
    return [translations.to_english(t) for t in naming.tokenize(name)]


cas = collections.Counter()
cas_by_cat = collections.defaultdict(collections.Counter)
lang = collections.Counter()
roots = collections.Counter()
junk = collections.Counter()
dupes = collections.Counter()
total = 0

# numbering: series key -> sorted list of (num, pad_width)
series = collections.defaultdict(list)
pad_hist = collections.Counter()
start_hist = collections.Counter()
per_parent_series = 0
global_candidates = collections.Counter()   # base -> distinct parents count

# affixes: rows = every object with its axis values; counts per affix/axis.
rows = []                                        # (name, {axis: value})
affix_total = collections.Counter()              # (kind, affix) -> count
affix_axis = collections.defaultdict(collections.Counter)  # (kind, affix, axis) -> Counter(value)
axis_total = collections.defaultdict(collections.Counter)  # axis -> Counter(value)

# semantic: container_name -> Counter(token -> count) over its descendants
cluster = collections.defaultdict(collections.Counter)

for f in args:
    with open(f, encoding="utf-8") as fh:
        d = json.load(fh)
    total += d.get("object_count", 0)
    for k, v in d.get("casing", {}).items():
        cas[k] += v
    for k, v in d.get("language", {}).items():
        lang[k] += v

    linked = build_tree(d)
    base_parents = collections.defaultdict(set)   # base -> set(parent id)
    names_here = collections.Counter()

    for nd, parent, root in linked:
        name = nd["name"]
        names_here[name] += 1
        if nd.get("depth", 0) == 0 and nd.get("children"):
            roots[name] += 1
        m = JUNK.match(name)
        if m:
            junk[m.group(1).lower()] += 1

        if naming is not None:
            cas_by_cat[nd.get("category", "other")][
                naming.detect_casing(name).value] += 1

        # numbering
        tm = TRAILING.match(name.strip())
        if tm and tm.group(1).strip(" _-"):
            base = tm.group(1).strip(" _-")
            digits = tm.group(2)
            num = int(digits)
            pad = len(digits) if digits.startswith("0") else 1
            pkey = id(parent) if parent is not None else None
            series[(pkey, base.lower())].append((num, pad))
            base_parents[base.lower()].add(pkey)

        # affix mining over all four axes
        axes = {
            "category": nd.get("category", "other"),
            "type": nd.get("type", "?"),
            "parent": parent["name"] if parent else "(root)",
            "root": root["name"] if root else "(root)",
        }
        rows.append((name, axes))
        for axis, value in axes.items():
            axis_total[axis][value] += 1
        pm = AFFIX_PRE.match(name)
        sm = AFFIX_SUF.search(name)
        for kind, match in (("pre", pm), ("suf", sm)):
            if not match:
                continue
            afx = match.group(1)
            affix_total[(kind, afx)] += 1
            for axis, value in axes.items():
                affix_axis[(kind, afx, axis)][value] += 1

        # semantic clusters: attribute leaf tokens to the enclosing container
        if parent is not None and not nd.get("children"):
            for t in english_tokens(name):
                t = re.sub(r"\d+$", "", t)   # Kontur01 clusters as 'kontur'
                if len(t) > 2:
                    cluster[parent["name"]][t] += 1

    for name, c in names_here.items():
        if c > 3:
            dupes[name] += c
    for base, parents in base_parents.items():
        if len(parents) > 1:
            global_candidates[base] += len(parents)


# ---- numbering aggregate ---------------------------------------------------
gapped = []
for (_pkey, base), items in series.items():
    if len(items) < 2:
        continue
    per_parent_series += 1
    nums = sorted(n for n, _ in items)
    pads = [p for _, p in items]
    pad_hist[max(pads)] += 1
    start_hist[nums[0]] += 1
    full = set(range(nums[0], nums[-1] + 1))
    missing = sorted(full - set(nums))
    if missing:
        gapped.append((base, nums, missing))


# ---- affix evaluation -------------------------------------------------------
def carries(name, kind, afx):
    return name.startswith(afx) if kind == "pre" else name.endswith(afx)


affix_findings = []
for (kind, afx), cnt in affix_total.most_common():
    if cnt < MIN_AFFIX_COUNT:
        continue
    # best axis explanation for this affix: maximize coverage * precision
    best = None
    for axis in AXES:
        for value, hits in affix_axis[(kind, afx, axis)].items():
            members = axis_total[axis][value]
            if members < MIN_AXIS_MEMBERS:
                continue
            coverage = hits / members
            precision = hits / cnt
            score = coverage * precision
            if coverage >= MIN_COVERAGE and precision >= MIN_PRECISION \
                    and (best is None or score > best["score"]):
                best = {"axis": axis, "value": value, "members": members,
                        "hits": hits, "coverage": coverage,
                        "precision": precision, "score": score}
    if best is None:
        affix_findings.append({"kind": kind, "affix": afx, "count": cnt,
                               "best": None})
        continue
    missing = [n for n, axes in rows
               if axes[best["axis"]] == best["value"]
               and not carries(n, kind, afx)]
    intruders = [n for n, axes in rows
                 if axes[best["axis"]] != best["value"]
                 and carries(n, kind, afx)]
    affix_findings.append({
        "kind": kind, "affix": afx, "count": cnt, "best": best,
        "missing": missing[:8], "missing_total": len(missing),
        "intruders": intruders[:5], "intruder_total": len(intruders),
    })


# ---- output ----------------------------------------------------------------
print("REPORTS  %d, objects total %d" % (len(args), total))
print("CASING  ", cas.most_common(6))
if cas_by_cat:
    print("CASING BY CATEGORY (deviations from the global style stand out)")
    for cat, hist in sorted(cas_by_cat.items()):
        print("   %-8s %s" % (cat, hist.most_common(3)))
print("LANG    ", lang.most_common())
print("ROOTS   ", roots.most_common(20))
print("JUNK    ", junk.most_common(10), "(default names -> rename candidates)")
print("DUPES   ", dupes.most_common(10), "(name >3x -> disambiguate/check)")

print("\n-- NUMBERING --")
print("series (>=2 members):", per_parent_series,
      "| padding hist (width->series):", dict(pad_hist),
      "| start index hist:", dict(start_hist.most_common(5)))
print("global (same base under >1 parent):",
      dict(global_candidates.most_common(8)),
      "-> per_parent likely" if global_candidates else "-> per_parent")
if gapped:
    print("gapped series (base -> nums -> missing), max 12:")
    for base, nums, missing in gapped[:12]:
        print("   %-24s %s  missing %s" % (base, nums[:12], missing[:12]))
else:
    print("no gaps found (series already gapless)")

print("\n-- AFFIXES (>=%dx; axis needs >=%d members, cov>=%.0f%%, prec>=%.0f%%) --"
      % (MIN_AFFIX_COUNT, MIN_AXIS_MEMBERS,
         MIN_COVERAGE * 100, MIN_PRECISION * 100))
if not affix_findings:
    print("   (no recurring prefixes/suffixes)")
for fx in affix_findings:
    label = "prefix" if fx["kind"] == "pre" else "suffix"
    if fx["best"] is None:
        print("   %-6s %-10s x%-4d no dominant axis (scattered -- probably "
              "not a convention)" % (label, fx["affix"], fx["count"]))
        continue
    b = fx["best"]
    print("   %-6s %-10s x%-4d %s=%r  coverage %d/%d (%.0f%%)  precision %.0f%%"
          % (label, fx["affix"], fx["count"], b["axis"], b["value"],
             b["hits"], b["members"], b["coverage"] * 100,
             b["precision"] * 100))
    if fx["missing_total"]:
        print("          would rename %d member(s) without it, e.g. %s"
              % (fx["missing_total"], fx["missing"]))
    if fx["intruder_total"]:
        print("          carried OUTSIDE the axis by %d, e.g. %s"
              % (fx["intruder_total"], fx["intruders"]))

print("\n-- SEMANTIC CLUSTERS (container -> top tokens) --")
# Affix letters are not semantics -- 'ABC_Kontur' clusters on 'kontur',
# never on 'abc' (that signal already lives in the AFFIXES section).
affix_tokens = {re.sub(r"[^A-Za-z]+", "", fx["affix"]).lower()
                for fx in affix_findings if fx["best"] is not None}
cluster_candidates = []
for container, toks in sorted(cluster.items(),
                              key=lambda kv: -sum(kv[1].values())):
    total_here = sum(toks.values())
    if total_here < 4:
        continue
    top = [(t, c) for t, c in toks.most_common(12)
           if t not in affix_tokens][:8]
    print("   %-22s %s" % (container, top))
    kws = [t for t, c in top if c >= 2 and t not in ("null", "object")]
    if kws:
        cluster_candidates.append((container, kws))

# ---- suggested rules (RuleV2 / structure dicts) ----------------------------
suggestions = {"rules": [], "structure": [], "unsupported": []}

if gapped:
    common_pad = pad_hist.most_common(1)[0][0] if pad_hist else 2
    suggestions["rules"].append({
        "id": "renumber_meshes",
        "type": "renumber",
        "match": {"categories": ["mesh"]},
        "pad": max(common_pad, 2),
        "start": start_hist.most_common(1)[0][0] if start_hist else 1,
        "per_parent": True,
    })


def axis_match(axis, value):
    if axis == "category":
        return {"categories": [value]}
    if axis == "type":
        return {"types": [value]}
    return {"under_group": value}   # parent/root container


for fx in affix_findings:
    if fx["best"] is None:
        continue
    b = fx["best"]
    slug = re.sub(r"[^A-Za-z0-9]+", "", fx["affix"]).lower() or "affix"
    if fx["kind"] == "pre":
        suggestions["rules"].append({
            "id": "prefix_%s_%s" % (slug, b["value"].lower().replace(" ", "_")),
            "type": "prefix",
            "prefix": fx["affix"],
            "match": axis_match(b["axis"], b["value"]),
            "_evidence": {
                "coverage": round(b["coverage"], 2),
                "precision": round(b["precision"], 2),
                "would_rename": fx["missing_total"],
                "intruders": fx["intruder_total"],
            },
        })
    else:
        suggestions["unsupported"].append({
            "kind": "suffix", "affix": fx["affix"],
            "axis": b["axis"], "value": b["value"],
            "coverage": round(b["coverage"], 2),
            "note": "engine has no suffix rule -- document, don't enforce",
        })

for container, kws in cluster_candidates[:8]:
    suggestions["structure"].append({
        "name": container,
        "keywords": kws,
        "aliases": [container.lower()],
        "priority": 40,
    })

print("\n-- SUGGESTED RULES (candidates, confirm in interview; strip "
      "_evidence before writing a preset) --")
print(json.dumps(suggestions, indent=2, ensure_ascii=True))

if json_out:
    with open(json_out, "w", encoding="utf-8") as fh:
        json.dump(suggestions, fh, indent=2, ensure_ascii=True)
    print("\n(suggestions written to %s)" % json_out)
