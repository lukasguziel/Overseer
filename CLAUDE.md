# CLAUDE.md — Scene Organizer

Context for Claude Code. Keep short and current.
**Binding conventions & gotchas: [.claude/rules.md](.claude/rules.md) — code and
comments are written in ENGLISH** (German only in translation data, test
fixtures, and user-facing UI copy).

## What this is

Cinema 4D 2024 plugin that **analyzes** scenes (interior/archviz), **normalizes
object names**, and **optimizes structure** (groups like Cameras/Lights/
Furniture/Exterior). Two UIs on the same logic: native C4D dialog **and** a web
frontend (Vite/React) with a node editor for the rule set.

User's production scene: `D:\3D\PROJECTS\01 - SAMPLE\sample_0070.c4d` (~2.3 GB).

**Key decision: plugin, NOT headless.** `c4dpy.exe` hangs on a license prompt →
all code runs as a plugin inside the licensed C4D GUI (details in rules.md).

## Architecture

**Core principle: pure domain logic strictly separated from `c4d`.**
`src/sceneorg/` never imports `c4d` → testable in CI. Only these modules import
`c4d` (never loaded by tests): `cinema/` (adapter/webapi), `bridge.py`.

```
src/
  scene_organizer.pyp     Loader. Registers ONE command "Scene Organizer" that
                          starts the server + opens the web UI (the only UI).
  sceneorg/
    config.py             config.json schema 3 (migrate_config reads v1/v2 forever;
                          per-section "accepted as-is" keeps map)
    bridge.py             [c4d] HTTP server (BG thread) + main-thread queue + progress
                          state. PROCESS SINGLETON — stays at package root.
    core/
      model.py            SceneNode / SceneTree (pure hierarchy)
      ops.py              plan_renames()/plan_reparents()/plan_layers() (scope, safety, prefixes)
      keeps.py            per-section "accepted as-is" lists (filter_kept/set_section_keeps)
      analyzer.py         SceneTree -> SceneReport (single pass)
      pipeline.py         plan_combined(): rules + naming + structure + layers in one
                          pass (backend of plan_all/apply_all, one-button flow)
    naming/
      casing.py           Tokenizer, casing detection, language heuristic (was naming.py)
      convention.py       NamingConvention (casing/language/numbering), disambiguate()
      translations.py     DE<->EN dictionary + add_translations()
      translate.py        Language-only rename proposals
      detect.py           Auto-detect existing scheme (style/language/pad + confidence)
    structure/
      standard.py         GroupRule / StructureStandard + evaluate() (was structure.py)
      rules.py            Declarative rule engine v2 (prefix/renumber/condition/layer,
                          Match vocabulary, compile_rules() -> RuleSet.plan_all())
      graph.py            node-editor graph incl. nested structure
    cinema/               [c4d] host glue
      adapter.py          doc <-> SceneTree; rename/reparent/plan/layers with undo
      webapi.py           JSON API; hot-reloaded per request. Scene-tree +
                          preview caches live on the `sceneorg` package
                          (survive hot-reload; invalidated by the doc dirty
                          counter, cleared by POST /api/reload). Every slow op
                          publishes a progress label (_OP_LABELS -> /api/progress).
  presets/  plans/        User-saved preset snapshots (schema 2, no shipped defaults)
                          / frozen restructuring plans (skill artifacts)
  web/                    Vite build output (gitignored; deployed by deploy.ps1)
frontend/                 Vite/React/TypeScript source (App.tsx, tabs/, components/, hooks/useOrganizer.ts)
tests/                    pytest, runs WITHOUT c4d
.github/workflows/ci.yml  4 jobs: plugin-lint (ruff), plugin-test (pytest, Python 3.12), frontend-lint (tsc), frontend-test (vitest + vite build)
.github/workflows/release.yml  builds SceneOrganizer-<version>.zip + creates a GitHub Release
                          (auto on v* tag push, or manually via workflow_dispatch with version input)
.claude/skills/deploy/    deploy skill incl. deploy.ps1 (copies .pyp + sceneorg/ +
                          presets/ + plans/ + web/ to the plugin dir) + machine-local
                          deploy.config.json (gitignored)
```

## Plugin IDs / port (scene_organizer.pyp)

Official Maxon base ID `1069217` ("GFCSceneOrganizer"):
`1069217` CommandData "Scene Organizer" (the only command; opens the web UI) ·
`1069220` ServerDialog ID. `1069218`/`1069219` are retired (former native
dialog / web command) — do not reuse them for anything else.
Web port `8787`. No MessageData — the ServerDialog timer drains the queue.

## Deployment

**Use the `deploy` skill** (`.claude/skills/deploy/` — script, config and docs
all live there). It discovers all installed Cinema 4D versions, asks which one
to target, and runs the skill's `deploy.ps1`. The target path is NEVER in the
repo: it lives in the machine-local, gitignored
`.claude/skills/deploy/deploy.config.json` (template: `deploy.config.example.json`
next to it). `deploy.ps1` reads that config (or an explicit `-Target <plugin dir>`);
Program Files targets need an elevated shell, the `%APPDATA%` prefs folder does not.

## Commands

```bash
python -m pytest                 # unit tests (no c4d), currently 103 green
python -m ruff check src tests   # lint (must be clean — CI gate)

cd frontend && pnpm run build    # output -> src/web/ (then deploy.ps1)
cd frontend && pnpm run dev      # HMR dev server, proxy /api -> localhost:8787
cd frontend && pnpm test         # vitest unit tests

powershell -File .claude/skills/deploy/deploy.ps1   # copy to the C4D plugin dir (target via deploy skill)
```

## Usage in C4D

After one restart: `Shift+C` → **"Scene Organizer"** (starts the server and
opens `http://127.0.0.1:8787`; keep the server dialog open — the web UI is
the only UI). Full API table:
`.claude/skills/scene-conventions/references/api.md`.

## What needs a restart?

- Pure `sceneorg` logic / `cinema/webapi.py`: **no restart, no
  even re-click** — `bridge.drain()` calls `reload_all()` on every API request, which
  purges all `sceneorg.*` submodules except `bridge` so the next request re-imports the
  edited source. Just deploy; the next browser action runs fresh code. `POST /api/reload`
  forces a purge on demand and returns the module count.
- Frontend: `pnpm run build` + deploy → reload browser. For a fast dev loop use
  `cd frontend && pnpm run dev` (Vite HMR, proxies `/api → localhost:8787`) — edits are
  live with no build/deploy; the C4D web server just needs to be running once.
- `bridge.py`, `webapi` entry signature, `.pyp`: C4D restart required (`bridge` is the
  process singleton and is deliberately excluded from `reload_all()`).

## Domain concepts (short)

- Categories: light, camera, null, mesh, spline, other.
- Producible casings: PascalCase, camelCase, lower_snake, UPPER_SNAKE, kebab
  (detection also knows UPPER/lower/Capitalized/spaced/mixed).
- NamingConvention: tokenize → translate (optional) → casing → padded number;
  idempotent. GroupRules match by category OR translated keywords; `aliases`
  map existing containers. Safety filter: only move objects whose parent is
  root or a Null (generator/deformer children untouched).
- config.json (next to the .pyp, **schema 2**): casing/language/number_pad/
  translations + nested `structure` tree + declarative `rules` list
  (prefix/renumber/condition/layer — see `sceneorg/structure/rules.py`). v1 configs
  (`prefixes`/`groups`) migrate automatically; `default_standard()` is
  Cameras+Lights only.
- Presets = complete settings snapshots `{schema:2, meta, settings}` saved by
  the user (`save_preset`) or generated by the skill. Apply writes the
  snapshot verbatim (no graph regeneration). No shipped default presets.
- One-button flow: `plan_all` (combined preview: naming+structure+layers,
  one tree read) → `apply_all` (server-side re-plan, accept lists per
  section, ONE undo step via `SceneAdapter.apply_bundle`).

## Current state / next step

Plugin runs (user-confirmed). Rule engine v2 + preset manager + one-button
apply are in place; the `scene-conventions` skill (replaces scene-architect +
scene-rules) analyzes exported reports, interviews the artist, and generates
presets. Open: run the skill on the user's real projects to co-develop the
actual rule set, then review it against the pro-artist checklist
(`.claude/skills/scene-conventions/references/review-checklist.md`).
