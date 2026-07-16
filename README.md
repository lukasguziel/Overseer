<!--
  Generated in a fixed, reproducible style — see .claude/skills/readme/SKILL.md.
  Detailed per-tab features live in docs/FEATURES.md; screenshots in
  docs/screenshots/ are regenerated from sample data.
-->

# Overseer

**Keep your Cinema 4D scenes organized — clean names, tidy structure, no
dead weight.**

[![Trailer](https://img.shields.io/badge/%E2%96%B6%20Trailer-watch-FF0000?logo=youtube&logoColor=white)](https://www.youtube.com/watch?v=jsoKxY_QdG0)
[![Download](https://img.shields.io/badge/Download-latest%20release-2ea44f?logo=github&logoColor=white)](https://github.com/lukasguziel/overseer/releases/latest)
[![Docs](https://img.shields.io/badge/Docs-feature%20tour-0969da?logo=readthedocs&logoColor=white)](docs/FEATURES.md)
[![Cinema 4D](https://img.shields.io/badge/Cinema%204D-2023%20%7C%202024-111111?logo=maxon&logoColor=white)](https://www.maxon.net/cinema-4d)
[![Support me](https://img.shields.io/badge/Support%20me-PayPal-00457C?logo=paypal&logoColor=white)](https://www.paypal.com/donate/?hosted_button_id=XSBBJYYEJZ7TE)

[![Watch the Overseer trailer](https://img.youtube.com/vi/jsoKxY_QdG0/maxresdefault.jpg)](https://www.youtube.com/watch?v=jsoKxY_QdG0)

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
  batch, and recolors the whole layer stack with an editable gradient —
  without moving anything.
- **Materials** — finds unused materials, oversized textures and missing
  maps — relink via file dialog, copy into the project, shrink in place, or
  clear dead refs.
- **Tags** — audits every tag: missing Phong tags, duplicate material tags,
  phong-angle spread with one-click alignment, and a grouped inventory with
  unified selection tags.
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
   [Releases](https://github.com/lukasguziel/overseer/releases).
2. Unzip the archive and copy the `Overseer` folder into your Cinema 4D
   `plugins` folder.
3. Restart Cinema 4D, then press `Shift+C` and search for **"Overseer"**.

## License

Overseer is free to use for personal and commercial projects, and you may
modify it for your own use. Selling it, bundling it into paid products, or
redistributing it as your own work is not permitted — see [LICENSE](LICENSE).

## Development

Pure domain logic (`src/overseer/`, no `c4d` import) is separated from the
C4D layer, so the test suite runs without Cinema 4D:

```bash
python -m pytest                 # unit tests (no c4d)
python -m ruff check src tests   # lint
cd frontend && pnpm run build    # web UI -> src/web/
powershell -File .claude/skills/deploy/deploy.ps1      # copy into the C4D plugin dir
```

`main` is the protected release branch: every merge into it rebuilds the zip
and refreshes the release of the version stamped in the repo. All work happens
on `feature/<topic>` branches; changes land via pull request.
Architecture, conventions and module docs: [AGENTS.md](AGENTS.md)
and [docs/](docs/).

## Support

[![Support me](https://img.shields.io/badge/Support_me-PayPal-red.svg)](https://www.paypal.com/donate/?hosted_button_id=XSBBJYYEJZ7TE)

Bugs & feature requests: [GitHub Issues](https://github.com/lukasguziel/overseer/issues).
