# overseer/updater.py

Generic, host-free auto-updater for GitHub-released plugin folders. Pure
stdlib, no `c4d`/`bpy`, fully testable in CI, and deliberately self-contained
(it duplicates a tiny `_writable` probe instead of importing `core.webio`) so
the single file can be dropped into other plugins of the same shape: a plugin
that *is* one folder, released as a zip asset whose top-level folder replaces
the install folder.

## The moving parts

- `UpdateTarget`: everything the updater needs to know about one install.
  `repo` ("owner/name"), `current_version`, `install_dir`, `data_dir`,
  `asset_pattern` (fnmatch over release asset names), `payload_marker` (a file
  that must exist at the payload root, rejects wrong/broken zips),
  `disable_globs` (loader files to neutralize in swapped-out copies) and
  `keep` (top-level entries that survive even when the zip ships them).
  Overseer's per-host profiles (`UPDATE_CINEMA`/`UPDATE_BLENDER`) live in
  `core/defaults.py`; `UPDATE_REPO` names the GitHub repo.
- `check(target)`: fetches `releases` from the GitHub API (unauthenticated,
  one request), filters to non-draft, non-prerelease entries whose assets match
  `asset_pattern`, and returns everything newer than `current_version`, newest
  first, **including each release's `body`** (the curated notes the release
  workflow writes) so the UI can show a changelog across skipped versions.
- `install(target, release)`: download the zip asset to a temp dir, extract
  (with a zip-slip guard), validate the payload root, then **swap**.

## The swap (why rename, not overwrite)

Windows will not let you delete or overwrite files a process has loaded
(`vendor/` ships Pillow `.pyd`s that Cinema holds open), but it will happily
*rename* them and their directory. So:

1. `install_dir` -> `install_dir.backup-<old version>` (rename, works even
   with loaded binaries; a collision gets a `-2` suffix),
2. the extracted payload root moves to `install_dir`,
3. every top-level entry of the backup that the payload does **not** ship
   (config.json, `history/`, `configs/`, caches, `dev_repo.txt`, ...) is
   copied into the new folder. User data is preserved *by construction*, no
   hand-maintained keep list (`keep` exists for overrides; `__pycache__` and
   the state file are excluded),
4. loader files in the backup are disabled, because the host would otherwise
   pick the backup up as a second copy: C4D scans the plugins dir recursively
   for `*.pyp` (-> `*.pyp.off`); Blender's extensions dir discovers any folder
   with a `blender_manifest.toml` (-> disabled too). A legacy Blender addons
   dir needs nothing extra, the dotted backup folder name is not an importable
   module.

A failure before step 2 completes renames the backup straight back. The swap
requires `swap_supported()` (install dir + parent writable); a Program Files
install refuses with an "update manually" error instead of half-working.

## Confirm / auto-restore lifecycle (`update_state.json` in `data_dir`)

`install()` writes `{state: "pending", from, to, backup, boots: 0}`. Then:

- **`note_boot(target)`**: called by each loader at host startup
  (`overseer.pyp` `main()`, the Blender addon `register()`). Increments
  `boots`; at `BOOT_LIMIT` (3) starts without a confirmation it assumes the
  update never came up and **rolls back**.
- **`confirm_ok(target)`**: called on every API request (WebApi `__init__`,
  one cheap file read). Flips pending -> ok **only after >= 1 boot**: the
  request right after an install still runs in the old session (hot-reload
  picks the new code up immediately), which proves the imports but not a clean
  restart. On confirm, older `.backup-*`/`.failed-*` siblings are pruned; the
  backup of THIS update is kept as cheap insurance.
- **`failed_start(target)`**: called from the C4D `Execute` exception path.
  A pending update whose command errors is rolled back immediately, and the
  error dialog says so.
- **`rollback()`**: current folder -> `install_dir.failed-<version>` (loaders
  disabled, kept for diagnosis), backup -> `install_dir`, loaders re-enabled,
  state `rolled_back`. The web UI shows the notice once; `update_ack`
  (`acknowledge()`) clears terminal states.

Honest limit: if the new loader itself cannot even be parsed, no plugin code
runs and nothing can auto-restore. The disabled backup next to the install
folder is the manual way back. The realistic failure (broken package import,
incomplete zip) is covered: the loader is tiny and rarely changes, and both
the boot counter and the `Execute` hook run from it.

## Where it is wired up

- Shared webapi ops `update_check` / `update_install` / `update_ack`
  (doc-independent, like `netinfo`), labels in `_OP_LABELS`; the check result
  is cached on the `overseer` package for `CHECK_TTL` (6 h), `{force: true}`
  bypasses. `HostContext.host_label` / `.update_profile` supply the per-host
  wording and asset shape.
- Frontend: `components/UpdateBanner.tsx` under the topbar. Availability +
  per-version notes (`lib/markdown.ts` subset renderer), Install with confirm,
  restart note, rolled-back notice.
- Downloads run on the host main thread like every other slow op (progress is
  published; the bridge submit timeout is 300 s).
