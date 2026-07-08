# bridge.py

HTTP bridge for the web frontend (c4d-dependent). The HTTP server runs on a background thread and enqueues each request; document accesses MUST run on the main thread, so requests are drained on the main thread and handed to `webapi.handle`.

Critical gotchas:
- This module is a **process-wide singleton** (queue + server state) and is INTENTIONALLY NOT hot-reloaded by the loader — otherwise the pending queue would be lost. Only the API logic (`sceneorg.cinema.webapi`) is freshly reloaded on every drain.
- Document/scene access is only legal on the main thread. The server thread never touches the doc directly; it submits and waits.

## Progress state
- `set_progress(phase, current, total, detail)` / `clear_progress()` / `get_progress()` — thread-safe (lock-guarded) progress record for the frontend preloader. Written by long-running main-thread operations, read by the SERVER thread. The `GET /api/progress` request is answered directly on the server thread WITHOUT going through the main-thread queue, so the preloader can poll while the main thread is busy with the very operation being reported.

## Request plumbing
- `_Request` — internal payload/result/error carrier with a `threading.Event` for cross-thread handoff.
- `submit(payload, timeout=60)` — called from the server thread: enqueues a request and blocks until the main thread sets the result. Raises `TimeoutError` if the main thread never processes it (means the server dialog was closed). Processing happens via the ServerDialog timer, so no MessageData/SpecialEventAdd is needed.
- `drain()` — called on the MAIN thread from the dialog timer: pops every queued request, hot-reloads `webapi`, runs `webapi.handle`, and signals each waiter. Empty queue returns immediately.

## HTTP server
- `_Handler` — `BaseHTTPRequestHandler`; serves `/api/*` via the queue and everything else as static files from the `web/` dir with an SPA fallback to `index.html`. Adds permissive CORS headers. The `progress` op short-circuits to the server-thread answer.
- `start(port=8787)` / `stop()` / `is_running()` — manage the daemon `ThreadingHTTPServer` singleton.

## Control dialog
- `ServerDialog(c4d.gui.GeDialog)` — control window that embeds the React frontend directly IN the C4D window via the native `CUSTOMGUI_HTMLVIEWER` gadget (QtWebEngine), same-origin as the API (no CORS/mixed-content issues). Falls back to the external browser if the viewer constant is unavailable. Its `Timer` drains the queue on the main thread; `DestroyWindow` stops the server. Subclasses must call `super().__init__()`.
- `open_panel(port=8787)` — starts the server and opens/reuses the dialog. Uses the ServerDialog plugin id `1069220` (derived from Maxon base ID `1069217`).

Restart note: changes to this module (queue/server signature, `.pyp` registration) require a full C4D restart; pure `webapi` logic does not.
