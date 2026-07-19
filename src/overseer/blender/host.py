"""Process-singleton host facade for the Blender backend.

The Blender twin of ``overseer.bridge.__init__``: owns the progress state, the
main-thread request queue, the HTTP server and the ``bpy.app.timers`` pump. It
is never purged by per-request hot reload (see ``reload.py``).

``ProgressState`` is inlined here (rather than imported from
``overseer.bridge.progress``) because importing anything under
``overseer.bridge`` would run ``bridge/__init__.py`` -> ``import c4d`` and fail
inside Blender.
"""
from __future__ import annotations

import os
import threading
import webbrowser

from .pump import MainThreadQueue
from .server import BridgeServer

# Drain the main-thread queue this often (seconds). Matches the ~25 ms cadence
# of the C4D ServerDialog timer closely enough for an interactive UI.
_PUMP_INTERVAL = 0.03


class ProgressState:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = {"active": False, "phase": "", "current": 0,
                       "total": 0, "detail": ""}

    def set(self, phase, current=0, total=0, detail=""):
        with self._lock:
            self._state.update(active=True, phase=str(phase),
                               current=int(current), total=int(total),
                               detail=str(detail))

    def clear(self):
        with self._lock:
            self._state.update(active=False, phase="", current=0, total=0,
                               detail="")

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._state)


def _prefs_config_paths():
    """Candidate config.json locations, most specific first (for the server's
    LAN/port probe on the background thread)."""
    paths = []
    try:
        import bpy
        base = bpy.utils.user_resource("CONFIG")
        if base:
            paths.append(os.path.join(base, "overseer", "config.json"))
    except Exception:
        pass
    # Plugin-dir sibling (dev checkout / addon root).
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    paths.append(os.path.join(root, "config.json"))
    return paths


progress = ProgressState()
requests = MainThreadQueue()
server = BridgeServer(progress, requests, config_paths=_prefs_config_paths)

_timer_registered = False


# --- facades (mirror bridge/__init__.py) -----------------------------------
def set_progress(phase, current=0, total=0, detail=""):
    progress.set(phase, current, total, detail)


def clear_progress():
    progress.clear()


def get_progress() -> dict:
    return progress.snapshot()


def submit(payload, timeout=300):
    return requests.submit(payload, timeout)


def drain():
    requests.drain()


def start(port=None) -> int:
    return server.start(port)


def stop():
    server.stop()


def is_running() -> bool:
    return server.is_running


def lan_enabled() -> bool:
    return server.lan_enabled


def server_port() -> int:
    return server.port


def _pump():
    """bpy.app.timers callback: drain queued requests on the main thread."""
    try:
        requests.drain()
    except Exception:
        pass
    return _PUMP_INTERVAL


def _register_timer():
    global _timer_registered
    if _timer_registered:
        return
    try:
        import bpy
        if not bpy.app.timers.is_registered(_pump):
            bpy.app.timers.register(_pump, persistent=True)
        _timer_registered = True
    except Exception:
        pass


# --- O(1) scene-edit epoch --------------------------------------------------
# BScene.dirty() must be cheap (it keys the scene cache and is polled on every
# request). Instead of an O(N) per-object hash, a depsgraph_update_post handler
# bumps a monotonic counter on any data edit (transform/geometry/rename), and
# load_post bumps it on file switch. This mirrors C4D's O(1) doc.GetDirty()
# native counter. Selection/camera moves are not depsgraph updates, so — like
# C4D's OBJECT|DATA dirty — they do NOT bump it.
_edit_epoch = 0
_handlers_registered = False
_pers_handler = None


def edit_epoch() -> int:
    return _edit_epoch


def bump_epoch() -> None:
    global _edit_epoch
    _edit_epoch += 1


def _on_edit(*args):
    # depsgraph_update_post -> (scene, depsgraph); load_post -> (path,). Accept
    # any signature and just advance the counter.
    global _edit_epoch
    _edit_epoch += 1


def _register_handlers():
    global _handlers_registered, _pers_handler
    if _handlers_registered:
        return
    try:
        import bpy
        from bpy.app.handlers import persistent
        # Apply @persistent at runtime (can't decorate at import: bpy is absent
        # in CI) so the handler survives .blend loads.
        if _pers_handler is None:
            _pers_handler = persistent(_on_edit)
        for lst in (bpy.app.handlers.depsgraph_update_post,
                    bpy.app.handlers.load_post):
            if _pers_handler not in lst:
                lst.append(_pers_handler)
        _handlers_registered = True
    except Exception:
        pass


def _unregister_handlers():
    global _handlers_registered
    try:
        import bpy
        for lst in (bpy.app.handlers.depsgraph_update_post,
                    bpy.app.handlers.load_post):
            if _pers_handler is not None and _pers_handler in lst:
                lst.remove(_pers_handler)
    except Exception:
        pass
    _handlers_registered = False


def _unregister_timer():
    global _timer_registered
    try:
        import bpy
        if bpy.app.timers.is_registered(_pump):
            bpy.app.timers.unregister(_pump)
    except Exception:
        pass
    _timer_registered = False


def shutdown() -> None:
    """Full teardown for addon unregister: stop the server, drop the timer and
    the edit-epoch handlers so a disabled addon leaves nothing running."""
    stop()
    _unregister_timer()
    _unregister_handlers()


def open_panel(port=None) -> int:
    """Start the server, register the main-thread pump + edit-epoch handlers,
    open the web UI."""
    port = start(port)
    _register_timer()
    _register_handlers()
    try:
        webbrowser.open("http://127.0.0.1:%d/" % port)
    except Exception:
        pass
    return port
