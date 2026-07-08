<!--
  This README is generated in a fixed, reproducible style.
  To update it (new features, changed UI): follow .claude/skills/readme/SKILL.md —
  it regenerates the screenshots below from sample data and prescribes the
  section format used here. Screenshots live in docs/screenshots/.
-->

# Scene Organizer

**Analyze, name and structure your Cinema 4D scenes — before they turn into a
1.2 GB mystery box.**

Scene Organizer is a Cinema 4D 2024 plugin for interior/archviz work. It
analyzes your scene, normalizes object names, translates them between
languages, groups loose objects, tags layers and cleans up materials &
textures — every change previewed first, applied per row or in bulk, and
undoable. Two UIs share the same logic: a native C4D dialog and a modern web
frontend.

All screenshots below show the plugin on a sample interior scene
(`penthouse_loft_final.c4d` — 1,847 objects, 40M polygons, 1.2 GB, mixed
German/English names). No marketing renders; this is the actual tool.

---

## Overview

Your scene's dashboard: how big, how healthy, and where to start.

- ✅ **Key tiles with trends** — objects, polygons, project size, each with a
  sparkline and delta from your analysis history. *Why: you notice the scene
  doubling in size before your render farm does.*
- ✅ **Health score with sub-rings** — naming, structure and materials each get
  a percentage; the rings jump straight to the matching tab. *Why: one number
  tells you whether the scene is delivery-ready.*
- ✅ **Cleanup workflow strip** — the recommended order (names → translation →
  layers → materials) with live todo counts per step. *Why: a process anyone
  can follow instead of guessing where to begin.*
- ✅ **Geometry treemap** — every object sized by polygon count; click a tile
  to select & frame it in the viewport. *Why: finds the 4.2M-polygon sofa
  that's eating your RAM in two seconds.*
- ✅ **Naming consistency & scene health cards** — casing/language
  distribution, default names, duplicates, empty groups.

![Overview](docs/screenshots/overview.png)

## Naming

Normalizes object names to **your** convention — casing, numbering,
duplicates — without ever touching the words themselves.

- ✅ **Live rename preview** — every proposed rename as `old → new`, tagged
  with the rule that caused it (casing / numbering / unique). *Why: no blind
  batch rename; you see exactly what changes and why.*
- ✅ **Per-row apply ✓ / accept-as-is ✕** — apply one rename immediately
  (undoable) or accept the current name; accepted names are remembered in the
  config and stop counting as todos. *Why: real scenes have intentional
  exceptions.*
- ✅ **Producible casings** — PascalCase, camelCase, lower_snake, UPPER_SNAKE,
  kebab; auto-detected from the scene's dominant style.
- ✅ **Keep separators mode** — recases words but keeps your `-`/`_`
  conventions (`Wand-01_test → WAND-01_TEST`).
- ✅ **Numbering & dedupe** — configurable zero-padding (01/001/…), duplicate
  names become unique (`Wall, Wall → Wall01, Wall02`).
- ✅ **Name cleanup lists** — default names (`Cube`, `Null`) and duplicates,
  each clickable to select & frame the object.

![Naming](docs/screenshots/naming.png)

## Translate

Rewrites object names into a target language, word by word — casing,
separators and numbers survive.

- ✅ **Offline dictionaries for 10 languages** — DE/FR/ES/IT/NL/PL/CS/PT/RU/TR
  → English (and back for German), no internet, no data leaves your machine.
  *Why: client scenes arrive in every language; delivery usually wants
  English.*
- ✅ **Google engine as opt-in** — any language pair when you need it, with a
  clear "names are sent to Google" warning and progress display.
- ✅ **Language detection** — per-name source language pills (DE 812 / EN 566)
  show what the scene is actually written in.
- ✅ **Word-level diff** — `Tuer_Eingang → Door_Entrance` with the exact word
  mapping in the tooltip. *Why: you can verify the dictionary did the right
  thing before applying.*
- ✅ **Per-row apply / accept-as-is** — the same uniform workflow as every
  other tab.

![Translate](docs/screenshots/translate.png)

## Assets

A searchable, sortable inventory of every object in the scene — and a batch
tool, not just a list.

- ✅ **Search + facets** — filter by name/type/layer text, category chips
  (mesh/light/camera/…), per-type facets, "only geometry" and "no layer"
  toggles. *Why: "show me every spline that isn't on a layer" is one click,
  not a scripting session.*
- ✅ **Sortable columns** — polygons, points, children, name, layer; find the
  heaviest objects instantly.
- ✅ **Multi-select with batch actions** — check rows, then *assign to layer*
  or *move to group* (targets autocomplete from the scene, created if
  missing, one undo step). *Why: reorganizing 40 objects should not mean 40
  drag-and-drops in the Object Manager.*
- ✅ **Click to focus** — any row selects & frames the object in the viewport.
- ✅ **Hidden-object awareness** — objects hidden in the Object Manager are
  marked and can be excluded from all stats.

![Assets](docs/screenshots/assets.png)

## Layers

The type axis of scene organization: tag lights, cameras and proxies onto C4D
layers **without moving a single object**.

- ✅ **Layer overview tree** — every layer with color, object count, polygon
  count and V/R/L flags, expandable down to the objects. *Why: layer chaos is
  invisible in the Object Manager.*
- ✅ **Tagging preview** — which object would land on which layer, per-row
  accept or skip, then one click to process. *Why: "toggle all lights" only
  works when all lights are actually on the Lights layer.*
- ✅ **Never touches the hierarchy** — layers are orthogonal to your spatial
  null structure; this tool keeps it that way.

![Layers](docs/screenshots/layers.png)

## Materials

Materials and the textures behind them — the invisible half of a scene's
size.

- ✅ **Unused-material detection** — with safety rails: materials used only by
  hidden objects are protected, and intentional keepers can be accepted
  (remembered in the config). *Why: deleting "unused" materials blindly is
  how hero assets lose their shader.*
- ✅ **Bulk delete with confirmation** — remove all deletable unused materials
  in one undoable step.
- ✅ **Texture inventory** — every map with real pixel size, disk size and a
  resolution tag (2K/4K/8K color-coded). *Why: the 8K texture that should be
  4K costs you render memory on every frame.*
- ✅ **Absolute-path fixer** — finds absolute texture paths, shows which ones
  live inside the project folder, and rewrites them to relative in one click.
  *Why: absolute paths break the moment the project moves machines.*
- ✅ **Missing-texture list** — see broken references before the render does.

![Materials](docs/screenshots/materials.png)

## Misc

Presets, exports, history — the plumbing that makes the rest trustworthy.

- ✅ **Presets** — complete settings snapshots (casing, translations, groups,
  rules); apply one and the whole tool follows that convention. *Why: switch
  between "my personal style" and "studio delivery spec" in one click.*
- ✅ **Change history with revert** — every tool action is logged with
  before → after per object; one click restores the previous state (again
  undoable). *Why: confidence to use batch tools at all.*
- ✅ **Scene export** — full hierarchy snapshot as JSON (for tooling/AI
  analysis) or CSV (for Excel), written next to your project file.
- ✅ **Analysis history** — object/polygon/size/compliance over time feeds the
  Overview trends.

![Misc](docs/screenshots/misc.png)

## The workflow in one paragraph

Analyze (automatic on open) → walk the workflow strip: fix **Naming** →
**Translate** what's left in the wrong language → tag **Layers** → clean
**Materials** → browse **Assets** for anything the batch tools missed. Every
step is previewed, per-row acceptable, applied as one undo step and logged in
the change history. Scope any step to the whole scene or just your current
C4D selection.

## Install

1. Download the latest `SceneOrganizer-<version>.zip` from
   [Releases](https://github.com/Goodsoup-Family-Crypt/scene-organizer/releases)
   and unpack it into your C4D plugins folder.
2. Restart Cinema 4D 2024, then `Shift+C` → **"Scene Organizer"** (native
   dialog) or **"Scene Organizer (Web)"** (starts a local server and opens
   `http://127.0.0.1:8787`; keep the server window open).

Program-Files installs work without elevation — everything the plugin writes
(config, histories, your presets) goes to your user prefs folder.

## Development

Pure domain logic (`src/sceneorg/`, no `c4d` import) is separated from the
C4D layer, so the test suite runs without Cinema 4D:

```bash
python -m pytest                 # unit tests (no c4d)
python -m ruff check src tests   # lint
cd frontend && pnpm run build    # web UI -> src/web/
powershell -File deploy.ps1      # copy into the C4D plugin dir
```

Architecture, conventions and module docs: [CLAUDE.md](CLAUDE.md) and
[docs/](docs/).

## Support

Scene Organizer is built at night, fueled by coffee, next to real archviz
deadlines. If it saved you an hour of renaming `Cube.1`:

**[♥ Buy me a coffee](https://www.buymeacoffee.com/bamerus)** — every donation
keeps the updates coming.

Bugs & feature requests: [GitHub Issues](https://github.com/Goodsoup-Family-Crypt/scene-organizer/issues).
