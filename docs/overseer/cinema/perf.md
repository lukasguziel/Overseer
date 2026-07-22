# cinema/perf.py

[c4d] Rebuild-cost audit: which generator stalls the viewport. Times how long
each generator/modifier takes to rebuild its cache so the heaviest branches can
be surfaced. Imports `c4d`; never loaded by the unit tests. Runs on the C4D
main thread.

## How it measures

A generator only rebuilds its cache when it is dirty, so the scan marks exactly
ONE object's cache dirty (`SetDirty(DIRTYFLAGS_CACHE)`) and times a full scene
pass (`ExecutePasses`). What the clock sees is that object's rebuild plus the
generators above it in the chain, which C4D has to rebuild too — that is real
cost, not an artifact: a heavy Cloner under a Subdivision Surface genuinely
drags the whole branch.

Nothing in the document changes — `DIRTYFLAGS_CACHE` only invalidates the
cache, it does not touch the object's data, so there is no undo step and no
dirty doc.

## Module constants

- `_BUILDFLAGS` / `_DIRTY_CACHE` — resolved via `getattr` with fallback ids so
  the module imports on C4D builds where the newer flag name is absent
  (`BUILDFLAGS_0` → `BUILDFLAGS_NONE` → 0; `DIRTYFLAGS_CACHE` → `DIRTYFLAGS_DATA`).
- `_REPEATS = 3` — how often each object is measured. The MEDIAN of the runs
  counts: a single hiccup (background process, GC pause) then cannot invent a
  hotspot, and an unlucky fast run cannot hide one. With 2 runs and
  "fastest wins", objects around the noise floor flickered in and out of the
  list between scans, hence 3 and a median.

## Functions

- `_exec_passes(doc)` — runs one scene pass and returns how long it took, in
  seconds.
- `_is_candidate(obj)` — True for objects flagged `OBJECT_GENERATOR` or
  `OBJECT_MODIFIER` (the only things with a rebuildable cache).
- `_type_label(obj)` — readable object type. C4D knows the name of every type
  it ships (incl. plugins and MoGraph), so ask it first via `GetTypeName()`;
  the hand-kept `KNOWN_TYPES` table is only a fallback, and a raw type id must
  never reach the screen.
- `_candidates` / `has_any` — collect (node, obj) candidate pairs / cheap check
  whether the scene has any candidate at all.
- `_scan(payload, doc, adapter, tree, progress)` — the audit. First a warm-up
  pass (everything gets built once), then a baseline: a timed pass with nothing
  dirty, which is the fixed overhead of a pass and is subtracted from every
  per-object measurement. `repeats` is clamped to 1..5.
  - Calibration pass: after per-object timing, rebuild EVERYTHING at once. If
    the per-object times were perfectly isolated they would add up to this;
    they add up to more when a generator sits under another one (rebuilding the
    child forces the parent too, so the parent's cost is counted in several
    children). The overlap ratio (`perf_logic.overlap_ratio`) tells the user
    how much to trust a single row.
- `_select(payload, ...)` — selects the objects named by `guids` in the
  document (`SELECTION_NEW` for the first, `SELECTION_ADD` for the rest).
- `handle(op, ...)` — dispatch for `perf_scan` / `perf_select`.

Ranking, median, jitter and overlap math live in the pure `core/perf_logic`.
