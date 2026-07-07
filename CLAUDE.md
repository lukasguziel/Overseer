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
`c4d` (never loaded by tests): `c4d_adapter.py`, `dialog.py`, `plugin_entry.py`,
`bridge.py`, `webapi.py`.

```
src/
  scene_organizer.pyp     Loader. Registers the plugins; hot-reload purges all
                          sceneorg modules EXCEPT sceneorg.bridge on each dialog call.
  sceneorg/
    model.py              SceneNode / SceneTree (pure hierarchy)
    naming.py             Tokenizer, casing detection, language heuristic
    translations.py       DE<->EN dictionary + add_translations()
    convention.py         NamingConvention (casing/language/numbering), disambiguate()
    detect.py             Auto-detect existing scheme (style/language/pad + confidence)
    structure.py          GroupRule / StructureStandard + evaluate(); default_standard()
    ops.py                plan_renames()/plan_reparents()/plan_layers() (scope, safety, prefixes)
    translate.py          Language-only rename proposals
    analyzer.py           SceneTree -> SceneReport (single pass)
    config.py / graph.py  config.json <-> Config; node-editor graph
    c4d_adapter.py        [c4d] doc <-> SceneTree; rename/reparent/plan/layers with undo
    dialog.py             [c4d] native GeDialog
    plugin_entry.py       [c4d] opens the dialog
    bridge.py             [c4d] HTTP server (BG thread) + main-thread queue. PROCESS SINGLETON.
    webapi.py             [c4d] JSON API; hot-reloaded per request
  presets/  plans/        Learned presets / frozen restructuring plans (skill artifacts)
  web/                    Vite build output (gitignored; deployed by deploy.ps1)
frontend/                 Vite/React source (App.jsx, RuleGraph.jsx, api.js)
tests/                    pytest, runs WITHOUT c4d
.github/workflows/ci.yml  ruff + pytest on Python 3.9 & 3.11
deploy.ps1                copies .pyp + sceneorg/ + presets/ + plans/ + web/ to the plugin dir
```

## Plugin IDs / port (scene_organizer.pyp)

Official Maxon base ID `1069217` ("GFCSceneOrganizer"), contiguous block:
`1069217` CommandData "Scene Organizer" · `1069218` dialog ID ·
`1069219` CommandData "Scene Organizer (Web)" · `1069220` ServerDialog ID.
Web port `8787`. No MessageData — the ServerDialog timer drains the queue.

## Deploy target

App-wide plugin folder (deploy.ps1 writes here → **needs admin**):
`C:\Program Files\Maxon Cinema 4D 2024\plugins\SceneOrganizer\`
Alternative without elevation: `%APPDATA%\Maxon\Maxon Cinema 4D 2024_A5DBFF93\plugins\SceneOrganizer\`.

## Commands

```bash
python -m pytest                 # unit tests (no c4d), currently 103 green
python -m ruff check src tests   # lint (must be clean — CI gate)

cd frontend && npm run build     # output -> src/web/ (then deploy.ps1)
cd frontend && npm run dev       # HMR dev server, proxy /api -> localhost:8787

powershell -File deploy.ps1      # copy to the C4D plugin dir
```

## Usage in C4D

After one restart: `Shift+C` → **"Scene Organizer"** (native dialog) or
**"Scene Organizer (Web)"** (starts server, opens `http://127.0.0.1:8787`;
keep the server dialog open). Full API table:
`.claude/skills/scene-architect/references/api.md`.

## What needs a restart?

- Pure `sceneorg` logic / `dialog.py` / `webapi.py`: no restart — deploy, click command again.
- Frontend: `npm run build` + deploy → reload browser.
- `bridge.py`, `webapi` entry signature, `.pyp`: C4D restart required.

## Domain concepts (short)

- Categories: light, camera, null, mesh, spline, other.
- Producible casings: PascalCase, camelCase, lower_snake, UPPER_SNAKE, kebab
  (detection also knows UPPER/lower/Capitalized/spaced/mixed).
- NamingConvention: tokenize → translate (optional) → casing → padded number;
  idempotent. GroupRules match by category OR translated keywords; `aliases`
  map existing containers. Safety filter: only move objects whose parent is
  root or a Null (generator/deformer children untouched).
- config.json (next to the .pyp) overrides casing/language/number_pad/
  prefixes/translations/groups; `default_standard()` is Cameras+Lights only.

## Current state / next step

Plugin runs (user-confirmed); web UI + node editor done. Presets + plan
execution (`/api/apply_preset`, `/api/apply_plan`) in place — the
`scene-architect` skill learns presets from exported reports and freezes
restructuring plans. Open: refine the real rule set from the user's scenes.
