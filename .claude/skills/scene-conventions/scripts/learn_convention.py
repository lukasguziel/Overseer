"""Deep convention learning across one or more reports (never reads a report
into the model context -- it aggregates and prints compact stats + suggested
RuleV2 dicts).

Usage: python learn_convention.py <report.json> [<report2.json> ...]
       python learn_convention.py reports/*.json

Sections:
  CASING / LANG        distribution over all names
  ROOTS                recurring top-level containers (= personal taxonomy)
  JUNK / DUPES         default-name and duplicate candidates
  NUMBERING            per sibling-series: gaps, padding distribution, start
                       index, per-parent vs global series
  PREFIXES             recurring ALL-CAPS/underscore prefixes and which
                       ancestor containers they correlate with
  SEMANTIC CLUSTERS    token co-occurrence within containers -> group-rule
                       candidates
  SUGGESTED RULES      JSON that maps directly onto RuleV2 / structure dicts

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
# Leading ALL-CAPS/underscore prefix, e.g. 'LGT_', 'KITCHEN_', 'A_'.
PREFIX = re.compile(r"^([A-Z0-9]{1,}[_])")
# Trailing number with its literal digits (to measure zero padding).
TRAILING = re.compile(r"^(.*?)[ _-]?(\d+)$")

if len(sys.argv) < 2:
    sys.exit("usage: learn_convention.py <report.json> [...]")


def build_tree(report):
    """Rebuild parent/child links from the flat preorder+depth node list.

    Returns a list of (node_dict, parent_dict_or_None). Report nodes stay
    plain dicts -- we only need name/depth/category for the stats.
    """
    linked = []
    stack = []   # (depth, node_dict)
    for nd in report.get("nodes", []):
        depth = nd.get("depth", 0)
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1] if stack else None
        linked.append((nd, parent))
        stack.append((depth, nd))
    return linked


def english_tokens(name):
    if naming is None:
        return [t.lower() for t in re.findall(r"[^\W\d_]+", name, re.UNICODE)]
    return [translations.to_english(t) for t in naming.tokenize(name)]


cas = collections.Counter()
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

# prefixes: prefix -> Counter(container_name -> count)
prefix_ctx = collections.defaultdict(collections.Counter)
prefix_total = collections.Counter()

# semantic: container_name -> Counter(token -> count) over its descendants
cluster = collections.defaultdict(collections.Counter)

for f in sys.argv[1:]:
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

    for nd, parent in linked:
        name = nd["name"]
        names_here[name] += 1
        if nd.get("depth", 0) == 0 and nd.get("children"):
            roots[name] += 1
        m = JUNK.match(name)
        if m:
            junk[m.group(1).lower()] += 1

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

        # prefix mining
        pm = PREFIX.match(name)
        if pm:
            pfx = pm.group(1)
            container = parent["name"] if parent else "(root)"
            prefix_ctx[pfx][container] += 1
            prefix_total[pfx] += 1

        # semantic clusters: attribute leaf tokens to the enclosing container
        if parent is not None and not nd.get("children"):
            for t in english_tokens(name):
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


# ---- output ----------------------------------------------------------------
print("REPORTS  %d, objects total %d" % (len(sys.argv) - 1, total))
print("CASING  ", cas.most_common(6))
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

print("\n-- PREFIXES (>=3x) --")
strong_prefixes = []
for pfx, cnt in prefix_total.most_common():
    if cnt < 3:
        continue
    ctx = prefix_ctx[pfx]
    top = ctx.most_common(4)
    # contextual = prefix concentrated under one/few containers
    dominant = top[0] if top else None
    contextual = dominant and dominant[1] >= 0.6 * cnt and dominant[0] != "(root)"
    strong_prefixes.append((pfx, cnt, top, contextual))
    print("   %-10s x%-4d containers=%s %s" % (
        pfx, cnt, top, "[contextual]" if contextual else "[global]"))
if not strong_prefixes:
    print("   (no recurring ALL-CAPS/underscore prefixes)")

print("\n-- SEMANTIC CLUSTERS (container -> top tokens) --")
cluster_candidates = []
for container, toks in sorted(cluster.items(),
                              key=lambda kv: -sum(kv[1].values())):
    total_here = sum(toks.values())
    if total_here < 4:
        continue
    top = toks.most_common(8)
    print("   %-22s %s" % (container, top))
    kws = [t for t, c in top if c >= 2 and t not in ("null", "object")]
    if kws:
        cluster_candidates.append((container, kws))

# ---- suggested rules (RuleV2 / structure dicts) ----------------------------
suggestions = {"rules": [], "structure": []}

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

for pfx, cnt, top, contextual in strong_prefixes:
    match = {}
    if contextual:
        match["under_group"] = top[0][0]
    suggestions["rules"].append({
        "id": "prefix_%s" % pfx.strip("_").lower(),
        "type": "prefix",
        "prefix": pfx,
        "match": match or {"name_regex": "^(?!%s)" % re.escape(pfx)},
    })

for container, kws in cluster_candidates[:8]:
    suggestions["structure"].append({
        "name": container,
        "keywords": kws,
        "aliases": [container.lower()],
        "priority": 40,
    })

print("\n-- SUGGESTED RULES (candidates, confirm in interview) --")
print(json.dumps(suggestions, indent=2, ensure_ascii=True))
