<!--
  Generated in a fixed, reproducible style — see .claude/skills/readme/SKILL.md.
  Detailed per-tab features live in docs/FEATURES.md; screenshots in
  docs/screenshots/ are regenerated from sample data.
-->

# Overseer

**Keep your Cinema 4D scenes organized — clean names, tidy structure, no
dead weight.**

Overseer is a Cinema 4D plugin for any kind of project. It analyzes
your scene and helps you keep it in shape: consistent object names,
translated wording, layers, tags, generator settings, external files and
materials & textures without leftovers. Every change is previewed first,
applied per row or in bulk, undoable, and logged — so batch cleanup stops
being scary. Your settings persist per project, presets make them portable.

![Overseer](docs/screenshots/overview.png)

## What it does

Full feature tour with screenshots: **[docs/FEATURES.md](docs/FEATURES.md)**

- **Overview** — dashboard with per-area health scores, size trends, a
  polygon treemap and a texture budget.
- **Naming** — normalizes names to your convention (casing, numbering,
  duplicates, kept special characters) with a live preview.
- **Translate** — rewrites names into your target language, via Google or
  offline dictionaries, with real source-language detection.
- **Layers** — gives every layerless object a layer, single or in one
  batch, without moving anything.
- **Materials** — finds unused materials, oversized textures and missing
  maps — relink via file dialog, copy into the project, or clear dead refs.
- **Tags** — audits every tag: missing Phong tags, duplicate material tags,
  phong-angle spread with one-click alignment.
- **Files** — inventory of external references (Alembic, caches, IES,
  audio/video) with missing-file relink and accept.
- **Assets** — searchable, sortable object inventory with batch actions
  (assign layer, move to group).
- **Generators** — compares settings across same-type generators (SDS
  subdivisions & co.) and aligns them in one undoable step.
- **Sims** — finds simulation setups that cost you silently: active on
  hidden objects, unbaked, or disabled leftovers.
- **Misc** — change history with revert and analysis history per scene.

## Installation

1. Grab the latest **`Overseer-<version>.zip`** from
   [Releases](https://github.com/lukasguziel/overseer/releases) —
   it ships fully built, nothing to compile.
2. Unpack it into your Cinema 4D `plugins` folder.
3. Restart Cinema 4D, then `Shift+C` → **"Overseer"** — it starts the
   local server and opens the UI at `http://127.0.0.1:8787` (keep the small
   server window open).

Program-Files installs work without elevation — everything the plugin
writes (config, histories, your presets) goes to your user prefs folder.

## Development

Pure domain logic (`src/sceneorg/`, no `c4d` import) is separated from the
C4D layer, so the test suite runs without Cinema 4D:

```bash
python -m pytest                 # unit tests (no c4d)
python -m ruff check src tests   # lint
cd frontend && pnpm run build    # web UI -> src/web/
powershell -File .claude/skills/deploy/deploy.ps1      # copy into the C4D plugin dir
```

Releases are built automatically from `main` by tagging `v*` (or manually
via the release workflow). Architecture, conventions and module docs:
[CLAUDE.md](CLAUDE.md) and [docs/](docs/).

## Support

Overseer is built at night, fueled by coffee, next to real
production deadlines. If it saved you an hour of renaming `Cube.1`:

**[♥ Buy me a coffee](https://www.paypal.com/paypalme/LukasGuziel)** — every
donation keeps the updates coming.

Bugs & feature requests: [GitHub Issues](https://github.com/lukasguziel/overseer/issues).
