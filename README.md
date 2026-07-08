<!--
  Generated in a fixed, reproducible style â€” see .claude/skills/readme/SKILL.md.
  Detailed per-tab features live in docs/FEATURES.md; screenshots in
  docs/screenshots/ are regenerated from sample data.
-->

# Scene Organizer

**Keep your Cinema 4D scenes organized â€” clean names, tidy structure, no
dead weight.**

Scene Organizer is a Cinema 4D plugin for any kind of project. It analyzes
your scene and helps you keep it in shape: consistent object names,
translated wording, layers for lights and cameras, grouped hierarchy, and
materials & textures without leftovers. Every change is previewed first,
applied per row or in bulk, undoable, and logged â€” so batch cleanup stops
being scary.

![Scene Organizer](docs/screenshots/overview.png)

## What it does

Full feature tour with screenshots: **[docs/FEATURES.md](docs/FEATURES.md)**

- **Overview** â€” dashboard with size/health trends, a polygon treemap and a
  guided cleanup workflow.
- **Naming** â€” normalizes names to your convention (casing, numbering,
  duplicates) with a live preview.
- **Translate** â€” rewrites names into your target language, offline for 10
  languages or via Google.
- **Assets** â€” searchable, sortable object inventory with batch actions
  (assign layer, move to group).
- **Layers** â€” tags lights, cameras and proxies onto C4D layers without
  moving a single object.
- **Materials** â€” finds unused materials, oversized textures, missing maps
  and absolute paths (with a one-click fix).
- **Misc** â€” presets, change history with revert, and JSON/CSV scene
  exports.

## Installation

1. Grab the latest **`SceneOrganizer-<version>.zip`** from
   [Releases](https://github.com/Goodsoup-Family-Crypt/scene-organizer/releases) â€”
   it ships fully built, nothing to compile.
2. Unpack it into your Cinema 4D `plugins` folder.
3. Restart Cinema 4D, then `Shift+C` â†’ **"Scene Organizer"** â€” it starts the
   local server and opens the UI at `http://127.0.0.1:8787` (keep the small
   server window open).

Program-Files installs work without elevation â€” everything the plugin
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

Scene Organizer is built at night, fueled by coffee, next to real
production deadlines. If it saved you an hour of renaming `Cube.1`:

**[â™¥ Buy me a coffee](https://www.buymeacoffee.com/bamerus)** â€” every
donation keeps the updates coming.

Bugs & feature requests: [GitHub Issues](https://github.com/Goodsoup-Family-Crypt/scene-organizer/issues).
