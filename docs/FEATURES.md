<!--
  Generated in a fixed, reproducible style — see .claude/skills/readme/SKILL.md.
  Section format: heading -> screenshot -> feature checklist.
  Screenshots live in docs/screenshots/ and are regenerated from sample data.
-->

# Features

Every area of the Scene Organizer web UI in detail. All changes across the
tool follow the same workflow: **preview first**, accept or skip per row,
apply as one undo step, and everything is logged in the change history.

## Overview

![Overview](screenshots/overview.png)

Your scene's dashboard: how big, how healthy, and where to start.

- ✅ **Key tiles with trends** — objects, polygons, project size, each with a
  sparkline and delta from your analysis history.
- ✅ **Health score with sub-rings** — naming, structure and materials each
  get a percentage; the rings jump straight to the matching tab.
- ✅ **Cleanup workflow strip** — the recommended order (names → translation →
  layers → materials) with live todo counts per step.
- ✅ **Geometry treemap** — every object sized by polygon count; click a tile
  to select & frame it in the viewport and find the heaviest assets in
  seconds.
- ✅ **Naming consistency & scene health cards** — casing/language
  distribution, default names, duplicates, empty groups.

## Naming

![Naming](screenshots/naming.png)

Normalizes object names to **your** convention — casing, numbering,
duplicates — without ever touching the words themselves.

- ✅ **Live rename preview** — every proposed rename as `old → new`, tagged
  with the rule that caused it (casing / numbering / unique).
- ✅ **Per-row apply ✓ / accept-as-is ✕** — apply one rename immediately
  (undoable) or accept the current name; accepted names are remembered in
  the config and stop counting as todos.
- ✅ **Producible casings** — PascalCase, camelCase, lower_snake, UPPER_SNAKE,
  kebab; auto-detected from the scene's dominant style.
- ✅ **Keep separators mode** — recases words but keeps your `-`/`_`
  conventions (`Wall-01_test → WALL-01_TEST`).
- ✅ **Numbering & dedupe** — configurable zero-padding (01/001/…), duplicate
  names become unique (`Wall, Wall → Wall01, Wall02`).
- ✅ **Name cleanup lists** — default names (`Cube`, `Null`) and duplicates,
  each clickable to select & frame the object.

## Translate

![Translate](screenshots/translate.png)

Rewrites object names into a target language, word by word — casing,
separators and numbers survive.

- ✅ **Offline dictionaries for 10 languages** — DE/FR/ES/IT/NL/PL/CS/PT/RU/TR
  → English (and back for German), no internet, no data leaves your machine.
- ✅ **Google engine as opt-in** — any language pair when you need it, with a
  clear "names are sent to Google" warning and progress display.
- ✅ **Language detection** — per-name source language pills (EN 1288 / DE 138)
  show what the scene is actually written in.
- ✅ **Word-level diff** — `Door_Entrance → Porte_Entree` with the exact word
  mapping in the tooltip, so you can verify the translation before applying.
- ✅ **Per-row apply / accept-as-is** — the same uniform workflow as every
  other tab.

## Assets

![Assets](screenshots/assets.png)

A searchable, sortable inventory of every object in the scene — and a batch
tool, not just a list.

- ✅ **Search + facets** — filter by name/type/layer text, category chips
  (mesh/light/camera/…), per-type facets, "only geometry" and "no layer"
  toggles.
- ✅ **Sortable columns** — polygons, points, children, name, layer; find the
  heaviest objects instantly.
- ✅ **Multi-select with batch actions** — check rows, then *assign to layer*
  or *move to group* (targets autocomplete from the scene, created if
  missing, one undo step).
- ✅ **Click to focus** — any row selects & frames the object in the viewport.
- ✅ **Hidden-object awareness** — objects hidden in the Object Manager are
  marked and can be excluded from all stats.

## Layers

![Layers](screenshots/layers.png)

The type axis of scene organization: tag lights, cameras and proxies onto
C4D layers **without moving a single object**.

- ✅ **Layer overview tree** — every layer with color, object count, polygon
  count and V/R/L flags, expandable down to the objects.
- ✅ **Tagging preview** — which object would land on which layer, per-row
  accept or skip, then one click to process.
- ✅ **Never touches the hierarchy** — layers are orthogonal to your spatial
  null structure; this tool keeps it that way.

## Materials

![Materials](screenshots/materials.png)

Materials and the textures behind them — the invisible half of a scene's
size.

- ✅ **Unused-material detection** — with safety rails: materials used only
  by hidden objects are protected, and intentional keepers can be accepted
  (remembered in the config).
- ✅ **Bulk delete with confirmation** — remove all deletable unused
  materials in one undoable step.
- ✅ **Texture inventory** — every map with real pixel size, disk size and a
  resolution tag (2K/4K/8K color-coded), sorted heaviest first.
- ✅ **Absolute-path fixer** — finds absolute texture paths, shows which ones
  live inside the project folder, and rewrites them to relative in one
  click.
- ✅ **Missing-texture list** — see broken references before the render does.

## Misc

![Misc](screenshots/misc.png)

Presets, exports, history — the plumbing that makes the rest trustworthy.

- ✅ **Presets** — complete settings snapshots (casing, translations, groups,
  rules); apply one and the whole tool follows that convention.
- ✅ **Change history with revert** — every tool action is logged with
  before → after per object; one click restores the previous state (again
  undoable).
- ✅ **Scene export** — full hierarchy snapshot as JSON (for tooling/AI
  analysis) or CSV (for Excel), written next to your project file.
- ✅ **Analysis history** — object/polygon/size/compliance over time feeds
  the Overview trends.
