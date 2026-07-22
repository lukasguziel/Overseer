# core/perf/logic.py

Pure ranking logic for the generator performance audit — no `c4d`, so it is
fully unit-tested in CI. The host measures how long ONE object takes to rebuild
its cache (`cinema/perf.py`); everything that turns those raw milliseconds
into a verdict lives here.

## Thresholds

- `NOISE_MS` (0.5) — a rebuild below this is noise (timer jitter), not a cost
  worth showing.
- `HEAVY_SHARE` (0.25) / `MID_SHARE` (0.08) — share of the measured total from
  which an object counts as the bottleneck / a heavy contributor. Relative,
  because "slow" only means anything next to the rest of the scene.

## Functions

- `level_for(share, ms) -> "heavy" | "mid" | "light"` — how much this object
  hurts the viewport; sub-noise rebuilds are always `light`.
- `median(samples)` — the middle sample, so one hiccup (a background process, a
  GC pause) cannot drag it the way it drags a mean.
- `jitter(samples)` — spread between the fastest and slowest run: how much to
  trust the value.
- `overlap_ratio(sum_ms, scene_ms)` — how much the per-object times overcount
  vs one full rebuild. `1.0` = the parts add up to the whole (each row is that
  object's own cost); `2.0` = the parts add up to twice the whole (nested
  generators, so a row is the cost of that object's whole BRANCH, not the object
  alone).
- `rank(entries)` — sort measurements slowest first and attach `share` + `level`
  to each. `entries` are `{guid, name, type, ms, polygons}` dicts. The summary's
  `slowest` names the single worst offender, but only when it is genuinely
  dominant (`level == "heavy"`) — a scene where everything costs the same has no
  bottleneck to name.
