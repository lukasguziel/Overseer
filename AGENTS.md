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
[hostapi.md](docs/ai/hostapi.md) (host contract) ·
[newhost.md](docs/ai/newhost.md) (**porting playbook — follow it when asked
to port Overseer to a new 3D app**).

## What this is

Cinema 4D plugin (tested with 2023 & 2024) for any kind of project: **analyzes** the scene for
insights, **normalizes object names**, and manages layers, tags, assets,
materials & textures. One UI: a web frontend (Vite/React) served by the plugin.

Tested against the user's ~2.3 GB production scene.

**Key decision: plugin, NOT headless.** `c4dpy.exe` hangs on a license prompt →
all code runs as a plugin inside the licensed C4D GUI (details in rules.md).

## Architecture

**Core principle: pure domain logic strictly separated from `c4d`.**
`src/overseer/` never imports `c4d` → testable in CI. Only these modules import
`c4d` (never loaded by tests): `cinema/` (adapter/webapi), `bridge/`.

```
src/
  plugin/                 per-host loader/entry files (ONLY what is custom to
                          one host's plugin format; everything else is shared)
    cinema4d/             overseer.pyp (loader: registers ONE command
                          "Overseer" that starts the server + opens the web UI,
                          the only UI), logo.png, config.example.json
    blender/              __init__.py (addon loader: bl_info + operator/panel)
                          + blender_manifest.toml
  overseer/
    config.py             config.json schema 3 (migrate_config reads v1/v2 forever;
                          per-section "accepted as-is" keeps map)
    updater.py            pure, reusable auto-updater: GitHub release check ->
                          zip download -> folder swap with backup -> confirm/
                          auto-rollback (docs/overseer/updater.md); ops
                          update_check/update_install/update_ack, UI banner
                          in frontend/src/components/UpdateBanner.tsx
    core/                 pure domain logic, ONE PACKAGE PER AREA (never imports
                          c4d/bpy -> fully tested in CI). Each area defines the
                          normalized report/plan shapes; the hosts only gather
                          their host-specific data into them.
      scene/              model.py (SceneNode/SceneTree), analyzer.py (SceneReport)
      naming/             casing.py (tokenizer/casing/language heuristic),
                          convention.py (NamingConvention), detect.py,
                          translate.py, translations.py + data/ dictionary packs
      organize/           ops.py (plan_renames/reparents/layers + Operation ABCs),
                          keeps.py ("accepted as-is"), journal.py (change journal)
      layers/             base.py (LayersBase template) + report.py
                          (LayerInfo, build_layer_report, mismatches)
      materials/          base.py (MaterialsBase: scan workflow,
                          internal-material rule, result shape)
      textures/           analysis.py (VRAM/resize decisions), imagesize.py,
                          thumbs.py (Pillow thumbnails)
      files/ generators/  audit.py: ONE Audit base class per area owning op
      sims/ tags/ perf/   dispatch, pure shaping (staticmethods) and the
                          result shapes; hosts subclass and implement only
                          the read/apply primitives (everything via self.)
      settings/           logic.py + io.py (per-project UI state persistence)
      hostapi/            ports.py (SceneHost/SceneAdapter/Audit/HostContext
                          ABCs) + webapi.py (the shared JSON op layer - all
                          /api op handlers, host-neutral)
      defaults.py         constant tables; webio.py  web/data-dir IO helpers
    cinema/               [c4d] host glue - mirrors the core areas 1:1:
                          scene/ (doc.py CDoc, readers.py, adapter.py),
                          organize/ (apply.py, journal.py), layers.py,
                          materials.py, textures/ (paths.py, resize.py,
                          previews.py), tags.py, generators.py, sims.py,
                          files.py, perf.py + webapi.py, constants.py,
                          context.py (HostContext; hot-reloaded per request)
      bridge/             HTTP server (BG thread) + main-thread queue + progress
                          state; one file per class (progress/mainthread/reload/
                          server/dialog). PROCESS SINGLETON — the whole package
                          is excluded from hot-reload.
    blender/              [bpy] host glue - same area layout as cinema/ (the
                          mirror makes host overrides visible: e.g. layers.py
                          implements the layers area on Blender collections).
                          host.py/pump.py/server.py/reload.py are the process
                          singleton (bpy.app.timers pump), scene/doc.py = BScene.
  web/                    Vite build output (gitignored; deployed by deploy.ps1)
frontend/                 Vite/React/TypeScript source (App.tsx, tabs/, components/, hooks/useOrganizer.ts)
  STYLEGUIDE.md           UI vocabulary: every reusable block, its class + markup
                          (.section-head, sidebar text ranks, buttons, colour meaning).
                          READ BEFORE touching CSS — reuse a block, never fork a near-copy.
tests/                    pytest, runs WITHOUT c4d/bpy, split per stack:
                          tests/core/<area>/ (pure domain), tests/cinema/
                          (compile + area-mirror gate), tests/blender/ (fakebpy
                          scene/webapi tests), tests/test_import_graph.py
                          (static import resolution across all stacks)
.github/workflows/ci.yml  4 jobs: plugin-lint (ruff), plugin-test (pytest, Python 3.11 =
                          C4D 2024 runtime; ruff enforces 3.9 syntax = C4D 2023),
                          frontend-lint (tsc), frontend-test (vitest + vite build);
                          runs on main + PRs
.github/workflows/release.yml  main = RELEASE BRANCH: every main push gates, builds
                          Overseer-<version>.zip and replaces the release of the
                          version stamped in the repo (tag moves along; version
                          gate checks pyproject/__init__/package.json agree).
                          main is PROTECTED (PR + green CI required, no direct
                          push): ALL work happens on feature/<topic> branches
                          (no permanent dev branch), a PR into main publishes.
                          The repo is lukasguziel/overseer (public home of
                          code, issues and releases — no mirror anymore).
.claude/skills/deploy/    deploy skill incl. deploy.ps1 (copies .pyp + overseer/ +
                          web/ to the plugin dir) + machine-local
                          deploy.config.json (gitignored)
```

## Plugin IDs / port (overseer.pyp)

Official Maxon base ID `1069217` (registered at Maxon under the historical
name "GFCSceneOrganizer" — the registration name never changes):
`1069217` CommandData "Overseer" (the only command; opens the web UI) ·
`1069220` ServerDialog ID. `1069218`/`1069219` are retired (former native
dialog / web command) — do not reuse them for anything else.
Web port: config.json `port`; each host REGISTERS its default in its own
`constants.py` (Cinema `8787`, Blender `8788`, separate ports so both hosts
can run side by side) — core carries no host values.
No MessageData — the ServerDialog timer drains the queue.

## Deployment

**Use the `deploy` skill** (`.claude/skills/deploy/` — script, config and docs
all live there). It discovers all installed Cinema 4D versions, asks which one
to target, and runs the skill's `deploy.ps1`. The target path is NEVER in the
repo: it lives in the machine-local, gitignored
`.claude/skills/deploy/deploy.config.json` (template: `deploy.config.example.json`
next to it). `deploy.ps1` reads that config (or an explicit `-Target <plugin dir>`);
Program Files targets need an elevated shell, the `%APPDATA%` prefs folder does not.

## Blender build

Same codebase also ships as a Blender addon (branch `feature/blender-port`).
Only the host glue differs — everything under `core/`, `naming/`, `config.py`
and the whole `frontend/` web UI is **shared verbatim** with the C4D build.
Read [docs/ai/blender.md](docs/ai/blender.md) BEFORE touching the port; only
`src/overseer/blender/` (and `src/plugin/blender/__init__.py`) may `import bpy`, and
never at module load (CI imports the host without Blender).

**Installable addon layout** — one top folder `overseer/` that *is* the package:
```
overseer/__init__.py   = src/plugin/blender/__init__.py  (addon loader: bl_info + operator)
overseer/overseer/     = src/overseer                (shared package incl. blender/)
overseer/web/          = src/web                      (Vite build)
overseer/vendor/       = src/vendor                   (Pillow, optional)
```

- **Dev deploy:** `powershell -File .claude/skills/deploy/deploy_blender.ps1`
  mirrors the tree into `<blender_config>/scripts/addons/overseer/`. Targets come
  from `-Target <addon dir>` or the optional per-user `blender_targets` list in
  `deploy.config.json` (see `deploy.config.example.json`).
- **Release zip:** `python scripts/release/build_blender_zip.py` writes
  `dist/Overseer-Blender-v<version>.zip` in the layout above — install via
  Blender's *Edit > Preferences > Add-ons > Install…*, then enable **Overseer**
  and open it from *View3D > Sidebar (N) > Overseer*.

## Commands

```bash
python -m pytest                 # unit tests (no c4d), must be green
python -m ruff check src tests   # lint (must be clean — CI gate)

cd frontend && pnpm run build    # output -> src/web/ (then deploy.ps1)
cd frontend && pnpm run dev      # HMR dev server, proxy /api -> localhost:8787
cd frontend && pnpm test         # vitest unit tests
cd frontend && pnpm run test:e2e # Playwright e2e per area (frontend/e2e/, fully mocked /api — no C4D; system Chrome)

powershell -File .claude/skills/deploy/deploy.ps1          # copy to the C4D plugin dir (target via deploy skill)
powershell -File .claude/skills/deploy/deploy_blender.ps1  # copy to a Blender scripts/addons/overseer/ dir
python scripts/release/build_blender_zip.py         # -> dist/Overseer-Blender-v<version>.zip
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
  idempotent.
- config.json (next to the .pyp, **schema 3**): casing/language/number_pad/
  translations + per-section `keeps` lists + machine-local `port`/`listen_lan`.
  `migrate_config()` reads old files forever and silently DROPS the retired
  rule-engine/preset era keys (`structure`, `rules`, `graph`, `preset`,
  `prefixes`, `groups`).

## Current state / next step

Plugin runs (user-confirmed), v1.0.0 released. The parked structure/rules
areas (group standard, rule engine v2, node editor, presets, one-button
apply, restructuring plans, "take my hand" guide) were REMOVED in July 2026
— only the Assets tab's "move to group" batch action still reparents
objects. The former scene-architect / scene-conventions / scene-rules
skills were removed earlier (unused); their API reference survives as
`docs/api.md`.
