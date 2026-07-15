# cinema/audit_files.py

[c4d] External-file audit: finds non-image asset references (Alembic caches,
IES, simulation caches, …) the scene depends on, flags the missing ones, and
can make paths relative, relink from a search folder, or pick a replacement by
hand. Imports `c4d`; never loaded by the unit tests. Runs on the C4D main
thread. Image textures are audited separately by the adapter's texture scan;
this module deliberately skips `fl.is_image` paths.

## Module constants

- `_OALEMBIC` — Alembic generator type id (fallback `1028083`).
- `_alembic_path_id()` — the `ALEMBIC_PATH` parameter id, or None on builds
  without it (the Alembic scan is then skipped).

## Functions

- `_generate_path(doc_path, raw)` — resolves a stored reference to an absolute
  path via `c4d.GenerateTexturePath` (honours the document's texture search
  paths).
- `_owner_name` / `_owner_kind` — the asset owner's display name and what it IS
  (object / material). `owner_kind` is recorded so the UI does not have to guess
  how to select it: an asset can also belong to a take or the render data, which
  is neither object nor material.
- `_guid_for(obj, adapter)` — reverse lookup of a `_by_guid` entry by object
  identity, with a fallback to the owner's `GetMain()`.
- `_entry(...)` — builds one result row: resolved path, existence, absolute vs
  relative, relocatability (`fl.relocatable`), on-disk size, owner and guid.
- `_asset_entries(...)` — walks `GetAllAssetsNew` (with caches) and turns every
  non-image asset into a row. Falls back gracefully if the API raises.
- `_alembic_entries(...)` — Alembic generators are not always reported by the
  asset API, so their `ALEMBIC_PATH` is read directly.
- `_kept_files()` — the user's "accepted as-is" missing-file list (from the
  keeps config), so acknowledged gaps stop showing as findings.
- `_scan(...)` — merges asset + Alembic rows, drops the document's own file
  (see below), dedupes by (kind, path, owner), pulls out accepted-missing rows,
  and sorts by on-disk size. `_is_own` drops the scene's own file; an unsaved
  document has no path, so its own entry never resolves and would otherwise show
  up as a missing file — it is matched by name instead.
- `_holders(adapter)` — iterates every object and material holder once (dedup by
  `id`), the set of things whose parameters may store a path.
- `_rewrite_everywhere(doc, adapter, raw, new_path)` — rewrites every parameter
  holding `raw` to `new_path`, across all holders, in the caller's undo bracket.
- `_prefer_relative(doc, path)` — shortens an absolute path to project-relative
  when the file lives under the project folder.
- `_pick_path(...)` — opens a load dialog and rewrites the chosen replacement
  everywhere. One undo step.
- `_relink(...)` — indexes a search folder by filename and relinks missing
  references by basename match. One undo step; progress every 200 files.
- `_make_relative(...)` — converts relocatable absolute paths to relative.
  Errors when the project is unsaved (no folder to relate to). Only Alembic
  paths are rewritten in place; other kinds are counted as skipped.
- `_select(...)` — selects the owners named by `guids`.
- `handle(op, ...)` — dispatch for `files_scan` / `files_make_relative` /
  `files_select` / `files_pick_path` / `files_relink`.

Path classification, relocatability and summary math live in the pure
`core/files_logic`.
