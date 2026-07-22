from __future__ import annotations

import c4d

from ..constants import DEFAULT_PORT
from .dialog import SERVER_DIALOG_ID, ServerDialog
from .mainthread import MainThreadQueue
from .progress import ProgressState
from .reload import reload_all
from .server import WEB_DIR, BridgeServer

__all__ = [
    "DEFAULT_PORT", "SERVER_DIALOG_ID", "WEB_DIR",
    "ProgressState", "MainThreadQueue", "BridgeServer", "ServerDialog",
    "progress", "requests", "server",
    "set_progress", "clear_progress", "get_progress",
    "submit", "drain", "reload_all",
    "start", "stop", "is_running", "lan_enabled", "server_port",
    "open_panel",
]

progress = ProgressState()
requests = MainThreadQueue()
server = BridgeServer(progress, requests)


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


_dialog = None


def open_panel(port=None) -> int:
    global _dialog
    port = start(port)

    if _dialog is None or not _dialog.IsOpen():
        _dialog = ServerDialog(port, requests, server)
        _dialog.Open(c4d.DLG_TYPE_ASYNC, pluginid=SERVER_DIALOG_ID,
                     defaultw=1200, defaulth=820)
    return port
