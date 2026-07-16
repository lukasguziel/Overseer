# AGENTS.md — Overseer

Context for AI coding agents, tool-agnostic (Claude Code loads it via the
`@AGENTS.md` import in the CLAUDE.md stub). Keep short and current.
**Binding conventions & gotchas: [docs/ai/rules.md](docs/ai/rules.md) — code and
comments are written in ENGLISH** (German only in translation data, test
fixtures, and user-facing UI copy).

**Package guides live in [docs/ai/](docs/ai/)** (moved out of the
source tree so the shipped code stays clean — nothing under `src/` but code).
READ the matching guide BEFORE working in that package:
[src.md](docs/ai/src.md) (plugin entry) ·
[overseer.md](docs/ai/overseer.md) (package root, bridge, config) ·
[cinema.md](docs/ai/cinema.md) (c4d host glue, every module + gotchas) ·
[core.md](docs/ai/core.md) · [naming.md](docs/ai/naming.md) ·
[structure.md](docs/ai/structure.md).

## What this is

Cinema 4D 2024 plugin for any kind of project: **analyzes** the scene for
insights, **normalizes object names**, **optimizes structure** (groups like
Cameras/Lights), and manages assets, materials & textures. Two UIs on the same
logic: native C4D dialog **and** a web frontend (Vite/React) with a node editor
for the rule set.

Tested against the user's ~2.3 GB production scene.

**Key decision: plugin, NOT headless.** `c4dpy.exe` hangs on a license prompt →
all code runs as a plugin inside the licensed C4D GUI (details in rules.md).

## Architecture

**Core principle: pure domain logic strictly separated from `c4d`.**
`src/overseer/` never imports `c4d` → testable in CI. Only these modules import
`c4d` (never loaded by tests): `cinema/` (adapter/webapi), `bridge/`.

```
src/
  overseer.pyp     Loader. Registers ONE command "Overseer" that
                          starts the server + opens the web UI (the only UI).
  overseer/
    config.py             config.json schema 3 (migrate_config reads v1/v2 forever;
                          per-section "accepted as-is" keeps map)
    bridge/               [c4d] HTTP server (BG thread) + main-thread queue + progress
                          state; one file per class (progress/mainthread/reload/
                          server/dialog). PROCESS SINGLETON — the whole package
                          is excluded from hot-reload.
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
      adapter/            doc <-> SceneTree; rename/reparent/plan/layers with undo.
                          One file per domain class (readers/scene/materials/
                          previews/texpaths/texresize/layers/apply/journal)
      webapi.py           JSON API; hot-reloaded per request. Scene-tree +
                          preview caches live on the `overseer` package
                          (survive hot-reload; invalidated by the doc dirty
                          counter, cleared by POST /api/reload). Every slow op
                          publishes a progress label (_OP_LABELS -> /api/progress).
  presets/  plans/        User-saved preset snapshots (schema 2, no shipped defaults)
                          / frozen restructuring plans (run via /api/apply_plan)
  web/                    Vite build output (gitignored; deployed by deploy.ps1)
frontend/                 Vite/React/TypeScript source (App.tsx, tabs/, components/, hooks/useOrganizer.ts)
  STYLEGUIDE.md           UI vocabulary: every reusable block, its class + markup
                          (.section-head, sidebar text ranks, buttons, colour meaning).
                          READ BEFORE touching CSS — reuse a block, never fork a near-copy.
tests/                    pytest, runs WITHOUT c4d
.github/workflows/ci.yml  4 jobs: plugin-lint (ruff), plugin-test (pytest, Python 3.12), frontend-lint (tsc), frontend-test (vitest + vite build); runs on dev + main + PRs
.github/workflows/release.yml  main = RELEASE BRANCH: every main push gates, builds
                          Overseer-<version>.zip and replaces the release of the
                          version stamped in the repo (tag moves along; version
                          gate checks pyproject/__init__/package.json agree).
                          main is PROTECTED (PR + green CI required, no direct
                          push): work happens on dev/feature branches, a PR into
                          main publishes. The repo is lukasguziel/overseer (public
                          home of code, issues and releases — no mirror anymore).
.claude/skills/deploy/    deploy skill incl. deploy.ps1 (copies .pyp + overseer/ +
                          presets/ + plans/ + web/ to the plugin dir) + machine-local
                          deploy.config.json (gitignored)
```

## Plugin IDs / port (overseer.pyp)

Official Maxon base ID `1069217` (registered at Maxon under the historical
name "GFCSceneOrganizer" — the registration name never changes):
`1069217` CommandData "Overseer" (the only command; opens the web UI) ·
`1069220` ServerDialog ID. `1069218`/`1069219` are retired (former native
dialog / web command) — do not reuse them for anything else.
Web port: config.json `port` (default `8787` in `core/defaults.py`).
No MessageData — the ServerDialog timer drains the queue.

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
python -m pytest                 # unit tests (no c4d), must be green
python -m ruff check src tests   # lint (must be clean — CI gate)

cd frontend && pnpm run build    # output -> src/web/ (then deploy.ps1)
cd frontend && pnpm run dev      # HMR dev server, proxy /api -> localhost:8787
cd frontend && pnpm test         # vitest unit tests
cd frontend && pnpm run test:e2e # Playwright e2e per area (frontend/e2e/, fully mocked /api — no C4D; system Chrome)

powershell -File .claude/skills/deploy/deploy.ps1   # copy to the C4D plugin dir (target via deploy skill)
```

## Usage in C4D

After one restart: `Shift+C` → **"Overseer"** (starts the server and
opens `http://127.0.0.1:8787`; keep the server dialog open — the web UI is
the only UI). Full API table: `docs/api.md`.

## What needs a restart?

- Pure `overseer` logic / `cinema/webapi.py`: **no restart, no
  even re-click** — `bridge.drain()` calls `reload_all()` on every API request, which
  purges all `overseer.*` submodules except `bridge` so the next request re-imports the
  edited source. Just deploy; the next browser action runs fresh code. `POST /api/reload`
  forces a purge on demand and returns the module count.
- Frontend: `pnpm run build` + deploy → reload browser. For a fast dev loop use
  `cd frontend && pnpm run dev` (Vite HMR, proxies `/api → localhost:8787`) — edits are
  live with no build/deploy; the C4D web server just needs to be running once.
- `bridge/`, `webapi` entry signature, `.pyp`: C4D restart required (`bridge` is the
  process singleton; the whole package is excluded from `reload_all()`).

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
  (prefix/renumber/condition/layer — see `overseer/structure/rules.py`). v1 configs
  (`prefixes`/`groups`) migrate automatically; `default_standard()` is
  Cameras+Lights only.
- Presets = complete settings snapshots `{schema:2, meta, settings}` saved by
  the user (`save_preset`). Apply writes the snapshot verbatim (no graph
  regeneration). No shipped default presets.
- One-button flow: `plan_all` (combined preview: naming+structure+layers,
  one tree read) → `apply_all` (server-side re-plan, accept lists per
  section, ONE undo step via `SceneAdapter.apply_bundle`).

## Current state / next step

Plugin runs (user-confirmed), v1.0.0 released. Rule engine v2 + preset
manager + one-button apply are in place. The former scene-architect /
scene-conventions / scene-rules skills were removed (unused); their API
reference survives as `docs/api.md`. Rule sets are built by hand in the web
UI's node editor and saved as presets.
