# overseer.pyp

Overseer loader plugin. Registers ONE CommandData at startup like any normal plugin — no startup risk, no MessageData, no submenu, single click launches it:
- "Overseer" → starts the local server + control dialog (whose timer drains the request queue on the main thread) and opens the web frontend.

Hot-reload: `overseer.webapi` is freshly loaded on every web request. EXCEPTION: `overseer.bridge` is the server/queue singleton and is never hot-reloaded. Only the initial registration requires one C4D restart.

Plugin IDs: Maxon-registered base ID `1069217` (registered under the historical name "GFCSceneOrganizer"); the other globally registered elements derive from it as a contiguous block (e.g. `1069220` async ServerDialog id in `bridge/dialog.py`). `CMD_MAIN = 1069217`. The web port is NOT defined here: `bridge.open_panel()` resolves it from `config.json` (`port`, default `core/defaults.DEFAULT_PORT` = 8787).

- `_ensure_path()` — inserts the plugin dir onto `sys.path` so `overseer` is importable.
- `_update_target()` / `_update_boot_guard()` / `_update_failed_start()` — auto-updater hooks (pure imports only, see `docs/overseer/updater.md`): `main()` counts this boot against a pending update and auto-restores the backup after `BOOT_LIMIT` unconfirmed starts; a failing `Execute` while an update is pending rolls back immediately and appends a restore note to the error dialog.
- `_load_icon()` — loads `logo.png` (next to the `.pyp`) as a 32×32 command icon; returns `None` on any failure so registration never breaks over the icon.
- `OverseerCommand(c4d.plugins.CommandData)` — `Execute` opens the web panel via `bridge.open_panel`; any exception is printed and shown in a MessageDialog rather than raised.
- `_safe(fn, what)` — runs a registration call and prints a traceback on failure instead of aborting plugin load.
- `main()` — runs the update boot guard, then registers the command plugin (with icon), each via `_safe`. Called at import time by the loader.
