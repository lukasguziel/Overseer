# core/journal

Pure data-model for the change journal (M2). No `c4d`, no file I/O — the c4d
BaseContainer/sidecar persistence lives in [cinema/adapter](../cinema/adapter.md)
(`load_journal` / `save_journal`) and the ops in
[cinema/webapi](../cinema/webapi.md).

A journal is a list of **run** entries (one apply-run = one entry):
`{id, ts, at, kind, summary, doc, items, revertible, reverted}`. Each item is a
recorded op `{sid, name, field, before, after, reverted}` where `field` is one
of `name` / `layer` / `parent`.

## Functions
- `normalize_entry(entry)` / `normalize_journal(entries)` — backfill the per-op
  `reverted` flag (legacy entries predate it), default `revertible`, sort by
  `ts`. Idempotent; run on every load so old journals keep working.
- `merge_journals(a, b)` — union two journals by entry `id`, newest `ts` wins.
  Reconciles the document BaseContainer copy with the sidecar file.
- `items_to_revert(entry, indices=None)` — `(index, item)` pairs still eligible
  for revert (skips already-reverted ops). `indices=None` selects the whole run
  (**full revert**); an explicit list selects individual ops (**per-op
  selective revert**). Out-of-range indices are ignored.
- `mark_reverted(entry, indices)` — flag those op indices reverted; when every
  op in the run is reverted the run's own `reverted` flips true.
- `set_entry(entries, entry)` — replace the same-id entry in place.

The adapter's `revert` returns a per-op `results` list (status
`reverted` / `missing` / `skipped`); webapi flags only the ops that actually
reverted, so a deleted/renamed target is skipped without aborting the run.
