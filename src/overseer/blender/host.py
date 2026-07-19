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


def open_panel(port=None) -> int:
    """Start the server, register the main-thread pump, open the web UI."""
    port = start(port)
    _register_timer()
    try:
        webbrowser.open("http://127.0.0.1:%d/" % port)
    except Exception:
        pass
    return port
