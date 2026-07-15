# src — Overseer plugin source

The C4D plugin entry point lives directly here (`overseer.pyp`); all pure,
`c4d`-free domain logic lives under `overseer/`.

## Files

### overseer.pyp
Loader. Registers ONE command ("Overseer", plugin id `1069217`) whose
`Execute` calls `overseer.bridge.open_panel()` — starting the HTTP server and
opening the web UI (the only UI). Web port `8787`.

- `main()` wraps each registration in `_safe()` (try/except that prints a
  traceback) so a failed register never aborts plugin load.
- `OverseerCommand.Execute` catches everything and shows the traceback in a
  `MessageDialog`; base-class subclasses must call `super().__init__()`.
- `_ensure_path()` inserts this dir on `sys.path` before importing `overseer`.
- The `help=` text and command `str=` passed to `RegisterCommandPlugin` are data
  arguments, not docstrings — keep them.

## Subpackages
- `overseer/` — the package root and all domain logic; see `overseer/CLAUDE.md`.

Per-module prose: see `docs/overseer.md`.
