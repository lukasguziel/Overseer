# Rules — Scene Organizer

Binding conventions and hard-won gotchas. CLAUDE.md links here; keep both current.

## Comments & docs

- **Source files carry NO module docstrings, NO function/class docstrings, and
  NO explanatory `#` comments.** A file starts directly with its first import
  (`from __future__ import annotations` first if present). The code explains the
  code; readability comes from clear names and logical blank-line grouping.
  - Keep ONLY functional pragma comments: `# noqa`, `# type:`, `# pragma:`,
    `# ruff:`, shebangs.
  - Group steps inside a function with blank lines (e.g. a blank line after an
    early `return` block before the next `try:`).
- **Prose explanation lives in `docs/`**, one markdown file per module,
  mirroring the source tree (`src/sceneorg/cinema/bridge.py` ->
  `docs/sceneorg/bridge.md`, `src/sceneorg/core/ops.py` ->
  `docs/sceneorg/core/ops.md`, `src/scene_organizer.pyp` ->
  `docs/scene_organizer.md`). Update the module's doc when you change its
  behavior. Hard-won c4d gotchas that used to sit in comments now live there.

## Language

- **All code, commit messages, and internal log/error strings are written in
  ENGLISH.** No German in source files. (Docs in `docs/` are English too.)
- Exceptions (deliberate German, do NOT "fix"):
  - `sceneorg/translations.py` — the DE→EN dictionary keys ARE German.
  - Test fixtures/asserts with German object names ("Möbel", "Küche", …) —
    they are inputs for language-detection/translation tests.
  - User-visible UI copy (web frontend texts) stays German — product
    decision, only change when asked.
- Python sources stay ASCII-only (encoding safety); UI strings may use umlauts.

## Code conventions

- New pure logic → `src/sceneorg/` (must NOT import `c4d`) + test in `tests/`.
  `python -m pytest` and `python -m ruff check src tests` must be green (CI gate).
- c4d-dependent code only in: `cinema/` (adapter/constants/webapi) and
  `bridge.py`. Tests never import these.
- Ruff config in `pyproject.toml` (UP031 %-format and UP042 StrEnum are
  deliberately ignored — Python 3.9 support).
- Syntax-check c4d modules without Cinema: `python -m py_compile <file>`
  (compiles, does not execute `import c4d`).

## Tests

- **Every test body is structured into three commented sections, in this
  order:** `# setup` (inputs/trees/configs), `# do it` (the call under test),
  `# postcondition` (the asserts). One blank line between sections, none
  between a section comment and its code. Omit a section that would be empty
  (e.g. `# setup` when fixtures provide everything) — never leave a dangling
  comment.
- These three section comments are the ONLY standalone comments allowed in a
  test (deliberate exception to the no-comments rule above). Extra explanation
  goes after a colon into the section line (`# postcondition: per-object layer
  is exposed in the node dicts`) or as a short trailing comment on the one
  assert it explains.
- Non-test helpers, fixtures (`conftest.py`), and parametrize decorators are
  not sectioned.

## OOP & data modelling

- **Prefer classes and interfaces over loose functions + dicts.** Model a
  concept as a `@dataclass` (data) or a class (behavior); reach for a plain dict
  only at the JSON boundary (`to_dict()` / API payloads).
- **Interfaces are `abc.ABC` + `@abstractmethod`** (explicit inheritance,
  `isinstance`-checkable), NOT `typing.Protocol`. Examples: `core/ops.Operation`
  and `core/ops.Writer`, `structure/rules.Rule`. A new op type subclasses
  `Operation`; a new rule type subclasses `Rule` and registers in `RULE_TYPES`.
- **Link data by reference, not by copied ids.** Objects that describe a scene
  node hold a live `node: SceneNode` and expose `guid`/`name`/… as read-through
  `@property`s (see `RenameOp`, `Finding`, `TranslateProposal`). The integer
  `guid` stays as the bridge back to the c4d document (write-back, accept lists),
  but is DERIVED from the node, never stored a second time.
  - On such dataclasses mark the `node` field `field(compare=False)` so equality
    stays shallow and never recurses through the parent/child graph.
- **Polymorphism over type-switches.** Give the base class the abstract method
  (`op.apply(writer)`, `rule.plan(ctx)`) and let each subclass implement it;
  avoid `if isinstance(...)` / `type ==` ladders at call sites.
- **No scattered module-level config constants.** Built-in domain defaults live
  in ONE place: pure ones in `core/defaults.py` (`LAYER_COLORS`,
  `DEFAULT_LAYER_SCHEME`, Redshift ids, …); c4d-bound tables (keyed by
  `c4d.O*`) in `cinema/constants.py`. User-facing settings belong in
  `config.json` (schema 2) and flow through `config.Config`. Do not define
  ad-hoc constant dicts inside a feature module.

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
