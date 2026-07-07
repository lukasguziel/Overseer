# Rules — Scene Organizer

Binding conventions and hard-won gotchas. CLAUDE.md links here; keep both current.

## Language

- **All code, comments, docstrings, commit messages, and internal log/error
  strings are written in ENGLISH.** No German in source files.
- Exceptions (deliberate German, do NOT "fix"):
  - `sceneorg/translations.py` — the DE→EN dictionary keys ARE German.
  - Test fixtures/asserts with German object names ("Möbel", "Küche", …) —
    they are inputs for language-detection/translation tests.
  - User-visible UI copy (C4D dialog labels in `dialog.py`, web frontend
    texts) stays German — product decision, only change when asked.
- Python sources stay ASCII-only (encoding safety); UI strings may use umlauts.

## Code conventions

- New pure logic → `src/sceneorg/` (must NOT import `c4d`) + test in `tests/`.
  `python -m pytest` and `python -m ruff check src tests` must be green (CI gate).
- c4d-dependent code only in: `c4d_adapter.py`, `dialog.py`, `plugin_entry.py`,
  `bridge.py`, `webapi.py`. Tests never import these.
- Ruff config in `pyproject.toml` (UP031 %-format and UP042 StrEnum are
  deliberately ignored — Python 3.9 support).
- Syntax-check c4d modules without Cinema: `python -m py_compile <file>`
  (compiles, does not execute `import c4d`).

## c4d plugin gotchas (each of these froze/blocked C4D at least once)

- **c4dpy is forbidden** — hangs on a stdin license prompt. Stuck `c4dpy.exe`
  processes hold the Maxon license and block C4D startup at "initializing
  plugins". First diagnosis on a slow/blocked start: `tasklist | grep -i c4dpy`,
  kill them all.
- **Plugin base classes (CommandData/MessageData/GeDialog): an overridden
  `__init__` MUST call `super().__init__()`** — otherwise the C++ part is
  corrupt and C4D freezes at startup. Prefer no `__init__` at all; do heavy
  imports lazily inside the event. Wrap every register line in the .pyp's
  `main()` in try/except.
- Document access only on the main thread → web requests go through the
  bridge queue; the ServerDialog timer (`SetTimer(100)`) drains it — only
  while that dialog is open. No MessageData (startup risk).
- Never add `sceneorg.bridge` to the hot-reload purge (process singleton:
  queue + HTTP server; purging loses requests).
- Changes to `bridge.py`, the `webapi` entry signature, or the `.pyp` need a
  full C4D restart; everything else hot-reloads (deploy → click command again).
- All write operations go through `doc.StartUndo/AddUndo/EndUndo` (one
  Ctrl+Z step).

## Data & channels

- `scene_report.json` (repo root) is how Claude sees the real scene — written
  by `/api/analyze`. Reports are 1–2 MB: never read fully, aggregate via the
  scripts in `.claude/skills/scene-conventions/scripts/`.
- Report `guid`s are traversal indices, valid only for that exact export.
  `apply_all` therefore re-plans server-side; accept lists are only valid
  within the same plan/apply request cycle.
- Config/preset **schema 2**: config.json = `{schema:2, casing, language,
  number_pad, translations, structure (nested tree), rules (typed list),
  graph, preset}`. `config.migrate_config()` reads v1 (`prefixes`/`groups`)
  forever; new files are written v2 only. Rule engine: `sceneorg/rules.py`
  (types: prefix/renumber/condition/layer), combined planning:
  `sceneorg/pipeline.py`.
- Presets are **user-created snapshots** (`save_preset` op / skill-generated):
  `{schema:2, meta:{id,name,description,created_at}, settings:<full config>}`
  in `src/presets/` resp. plugin `presets/`. No shipped default presets.
  `deploy.ps1` MERGES presets (never deletes user-saved ones in the plugin).
- Restructuring plans in `src/plans/`. Formats + full API table:
  `.claude/skills/scene-conventions/references/`.
- Nested structure rules fixed the old flat-model false negative, but still:
  do not auto-"repair" structure blindly on flat scenes — check the
  compliance evidence first; Translate/Layers are the safer defaults.
