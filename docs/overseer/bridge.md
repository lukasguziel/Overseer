# bridge/ (package)

HTTP bridge for the web frontend (c4d-dependent). The HTTP server runs on a background thread and enqueues each request; document accesses MUST run on the main thread, so requests are drained on the main thread and handed to `webapi.handle`. One file per class:

```
bridge/
  __init__.py    singletons (progress/requests/server) + facade functions + open_panel()
  progress.py    ProgressState
  mainthread.py  MainThreadRequest, MainThreadQueue
  reload.py      reload_all() (hot-reload purge)
  server.py      RequestHandler, BridgeServer (+ WEB_DIR, CONTENT_TYPES)
  dialog.py      ServerDialog (+ SERVER_DIALOG_ID)
```

Critical gotchas:
- The package is a **process-wide singleton** (queue + server state) and is INTENTIONALLY NOT hot-reloaded: `reload.reload_all()` keeps `overseer.bridge` AND every `overseer.bridge.*` submodule (purging a submodule would let a later import create a second, empty singleton). Only the API logic (`overseer.cinema.webapi`) is freshly reloaded on every drain.
- Document/scene access is only legal on the main thread. The server thread never touches the doc directly; it submits and waits.
- webapi (hot-reloaded) must ONLY talk to bridge through the `__init__` facade functions — after a deploy the RUNNING bridge instance predates the new source until a C4D restart, so webapi additionally hedges with `getattr` when it uses newer bridge attributes.

## progress.py — ProgressState (instance: `progress`)
`set(phase, current, total, detail)` / `clear()` / `snapshot()` — thread-safe (lock-guarded) progress record for the frontend preloader. Written by long-running main-thread operations, read by the SERVER thread. The `GET /api/progress` request is answered directly on the server thread WITHOUT going through the main-thread queue, so the preloader can poll while the main thread is busy with the very operation being reported. Facades: `set_progress` / `clear_progress` / `get_progress`.

## mainthread.py — MainThreadQueue (instance: `requests`)
- `MainThreadRequest` — payload/result/error carrier with a `threading.Event` for cross-thread handoff.
- `submit(payload, timeout=300)` — called from the server thread: enqueues a request and blocks until the main thread sets the result. Raises `TimeoutError` if the main thread never processes it (means the server dialog was closed).
- `drain()` — called on the MAIN thread from the dialog timer: pops every queued request, dispatches it, and signals each waiter. Empty queue returns immediately. Processing happens via the ServerDialog timer, so no MessageData/SpecialEventAdd is needed.
- `_dispatch(payload)` — hot-reloads via `reload_all()`, then runs `webapi.handle`. The `reload` op short-circuits: it only purges and clears the cross-request scene cache on the `overseer` package, returning the purge count.

## server.py — RequestHandler + BridgeServer (instance: `server`)
- `RequestHandler` — `BaseHTTPRequestHandler`; serves `/api/*` via the queue and everything else as static files (`CONTENT_TYPES`) from the `web/` dir with an SPA fallback to `index.html`. Adds permissive CORS headers. Reaches the singletons via `self.server.progress` / `self.server.requests` — `BridgeServer.start` pins them onto the `ThreadingHTTPServer` instance (dependency injection instead of module globals).
- `BridgeServer(progress, requests)` — manages the daemon `ThreadingHTTPServer`: `start(port=None)` / `stop()` and the read-only properties `port`, `lan_enabled`, `is_running` (facades: `start`/`stop`/`is_running`/`lan_enabled`/`server_port`).
- Server settings come from `config.json` at server start: `port` (default `core/defaults.DEFAULT_PORT` = 8787; an explicit `start(port)` argument wins) and `listen_lan`. Candidates are checked in order — per-user prefs dir `overseer/config.json`, then the legacy `scene_organizer/config.json` (webapi migrates it on first write, but the server may start before any API call ran), then the plugin dir — and the first readable file wins. Evaluated ONCE at server start; changing either value requires a C4D restart, like everything in this package.
- `listen_lan` binds `0.0.0.0` instead of `127.0.0.1`, which exposes the UI (and its scene-mutating API!) to the local network — for the scan-a-QR-code-on-your-phone flow. Strictly opt-in.

## dialog.py — ServerDialog
`ServerDialog(port, requests, server)` — control window that embeds the React frontend directly IN the C4D window via the native `CUSTOMGUI_HTMLVIEWER` gadget (QtWebEngine), same-origin as the API (no CORS/mixed-content issues). Falls back to the external browser if the viewer constant is unavailable. Its `Timer` drains the injected queue on the main thread; `DestroyWindow` stops the injected server. Subclasses must call `super().__init__()`.

## __init__.py
Builds the three singletons, exposes the facade functions, re-exports `DEFAULT_PORT` (compat for older webapi builds), and provides `open_panel(port=None)` — starts the server and opens/reuses the dialog under plugin id `SERVER_DIALOG_ID` `1069220` (derived from Maxon base ID `1069217`).

Restart note: changes to this package (queue/server signature, `.pyp` registration) require a full C4D restart; pure `webapi` logic does not.
