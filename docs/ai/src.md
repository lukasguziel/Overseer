# src â€” Overseer plugin source

Per-host plugin entry points live under `plugin/` (`plugin/cinema4d/` with
`overseer.pyp` + `logo.png` + `config.example.json`, `plugin/blender/` with the
addon `__init__.py` + `blender_manifest.toml`); all pure, `c4d`-free domain
logic lives under `overseer/`. Deployed layouts are unchanged: the loader
always ends up at the root of the installed plugin/addon folder.

## Files

### plugin/cinema4d/overseer.pyp
Loader. Registers ONE command ("Overseer", plugin id `1069217`) whose
`Execute` calls `overseer.bridge.open_panel()` â€” starting the HTTP server and
opening the web UI (the only UI). The web port comes from config.json `port`
(default `8787` in `overseer/core/defaults.py`), resolved inside the bridge.

- `main()` wraps each registration in `_safe()` (try/except that prints a
  traceback) so a failed register never aborts plugin load.
- `OverseerCommand.Execute` catches everything and shows the traceback in a
  `MessageDialog`; base-class subclasses must call `super().__init__()`.
- `_ensure_path()` inserts this dir on `sys.path` before importing `overseer`.
- The `help=` text and command `str=` passed to `RegisterCommandPlugin` are data
  arguments, not docstrings â€” keep them.

## Subpackages
- `overseer/` â€” the package root and all domain logic; see [overseer.md](overseer.md).

Per-module prose: see `docs/plugin/cinema4d.md`.
