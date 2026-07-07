"""HTTP bridge for the web frontend (c4d-dependent).

Important: document accesses MUST run on the main thread. The HTTP server
runs on a background thread and puts each request into a queue; a
MessageData plugin (registered in the .pyp) drains the queue via
SpecialEventAdd on the main thread and calls `webapi.handle`.

This module is a process-wide singleton (queue + server state) and is
INTENTIONALLY NOT hot-reloaded by the loader -- otherwise the queue would
be lost. The actual API logic (`webapi`) is freshly loaded on every drain.
"""

from __future__ import annotations

import http.server
import importlib
import json
import os
import queue
import threading
import traceback
import webbrowser

import c4d

DEFAULT_PORT = 8787
_SRV_DIALOG_ID = 1069220  # derived from Maxon base ID 1069217
WEB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

_server = None
_thread = None
_queue: queue.Queue = queue.Queue()

# ---------------------------------------------------------------------------
# Progress state (preloader). Written by long-running main-thread operations
# (webapi/adapter), read by the SERVER thread via GET /api/progress -- that
# request is answered directly WITHOUT the main-thread queue, otherwise it
# would be stuck behind the very operation it reports on. Lives in this
# module because bridge is the process singleton (never hot-reloaded).
# ---------------------------------------------------------------------------
_progress_lock = threading.Lock()
_progress = {"active": False, "phase": "", "current": 0, "total": 0, "detail": ""}


def set_progress(phase, current=0, total=0, detail=""):
    with _progress_lock:
        _progress.update(active=True, phase=str(phase), current=int(current),
                         total=int(total), detail=str(detail))


def clear_progress():
    with _progress_lock:
        _progress.update(active=False, phase="", current=0, total=0, detail="")


def get_progress() -> dict:
    with _progress_lock:
        return dict(_progress)

_CTYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript",
    ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml",
    ".ico": "image/x-icon", ".png": "image/png", ".woff2": "font/woff2",
    ".map": "application/json",
}


class _Request:
    __slots__ = ("payload", "event", "result", "error")

    def __init__(self, payload):
        self.payload = payload
        self.event = threading.Event()
        self.result = None
        self.error = None


def submit(payload, timeout=60):
    """From the server thread: enqueue a request and wait for the result.

    Processing happens on the main thread via the ServerDialog's timer
    (see below) -> NO MessageData/SpecialEventAdd needed, hence no
    startup risk.
    """
    req = _Request(payload)
    _queue.put(req)
    if not req.event.wait(timeout):
        raise TimeoutError("Main-thread timeout (keep the server dialog open)")
    if req.error:
        raise RuntimeError(req.error)
    return req.result


def drain():
    """On the MAIN thread (from MessageData.CoreMessage): process the queue."""
    while True:
        try:
            req = _queue.get_nowait()
        except queue.Empty:
            return
        try:
            from .cinema import webapi
            importlib.reload(webapi)  # hot-reload of the API logic
            req.result = webapi.handle(req.payload)
        except Exception:
            req.error = traceback.format_exc()
        finally:
            req.event.set()


class _Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, *args):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/"):
            return self._api("GET")
        return self._static()

    def do_POST(self):
        if self.path.startswith("/api/"):
            return self._api("POST")
        self._json({"error": "not found"}, 404)

    def _api(self, method):
        try:
            payload = {}
            if method == "POST":
                length = int(self.headers.get("Content-Length", 0) or 0)
                if length:
                    payload = json.loads(self.rfile.read(length) or b"{}")
            payload["op"] = self.path[len("/api/"):].split("?")[0]
            if payload["op"] == "progress":
                # Answered on the server thread (no doc access) so the
                # preloader can poll WHILE the main thread is busy.
                return self._json(get_progress())
            self._json(submit(payload))
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _static(self):
        path = self.path.split("?")[0]
        if path in ("/", ""):
            path = "/index.html"
        full = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            # SPA fallback to index.html
            full = os.path.join(WEB_DIR, "index.html")
            if not os.path.isfile(full):
                self.send_response(404)
                self.end_headers()
                return
        ctype = _CTYPES.get(os.path.splitext(full)[1].lower(),
                            "application/octet-stream")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start(port=DEFAULT_PORT):
    global _server, _thread
    if _server is not None:
        return port
    _server = http.server.ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True)
    _thread.start()
    return port


def stop():
    global _server, _thread
    if _server is not None:
        _server.shutdown()
        _server.server_close()
        _server = None
        _thread = None


def is_running():
    return _server is not None


# --------------------------------------------------------------------------
# Server control dialog: drains the queue via timer on the main thread.
# Web requests are processed as long as this window is open.
# --------------------------------------------------------------------------

_BTN_OPEN = 3001
_BTN_STOP = 3002
_BTN_RELOAD = 3003
_ID_HTMLVIEW = 3010
_dialog = None


class ServerDialog(c4d.gui.GeDialog):
    """Control dialog WITH embedded web frontend.

    The React bundle is rendered not in an external browser but directly IN
    this C4D window -- via the native CUSTOMGUI_HTMLVIEWER gadget
    (QtWebEngine). The viewer points to http://127.0.0.1:<port>/, i.e. the
    same origin that also serves the app + /api/* -> `fetch('/api/..')`
    in the frontend runs same-origin, no CORS, no file:// mixed content.

    If CUSTOMGUI_HTMLVIEWER is unavailable (older C4D builds), the classic
    browser button remains as a fallback.
    """

    def __init__(self, port):
        super().__init__()
        self._port = port
        self._html_gui = None

    def _url(self):
        return "http://127.0.0.1:%d/" % self._port

    def CreateLayout(self):
        self.SetTitle("Scene Organizer")
        # Only the viewer, fills the whole window. Debug actions (Reload/Open/
        # Stop) live in the web UI under Misc -> Debug; closing the window
        # stops the server (see DestroyWindow).
        self.GroupBegin(1000, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, rows=1)
        self.GroupBorderSpace(6, 6, 6, 6)

        html_constant = getattr(c4d, "CUSTOMGUI_HTMLVIEWER", None)
        if html_constant is None:
            # No embedded viewer -> open in the external browser.
            self.AddStaticText(
                0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
                name="Opened in your browser (HtmlViewer not available here).")
            try:
                webbrowser.open(self._url())
            except Exception:
                pass
        else:
            settings = c4d.BaseContainer()
            self._html_gui = self.AddCustomGui(
                _ID_HTMLVIEW, html_constant, "",
                c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, 1180, 760, settings)
        self.GroupEnd()
        return True

    def InitValues(self):
        self.SetTimer(100)  # ms -> Timer() drains the queue on the main thread
        self._load()
        return True

    def _load(self):
        if self._html_gui is None:
            return
        url = self._url()
        try:
            self._html_gui.SetUrl(url)
        except Exception:
            try:
                self._html_gui.SetUrl(url, 0)
            except Exception:
                pass

    def Timer(self, msg):
        drain()

    def Command(self, cid, msg):
        if cid == _BTN_OPEN:
            webbrowser.open(self._url())
        elif cid == _BTN_RELOAD:
            self._load()
        elif cid == _BTN_STOP:
            self.Close()
        return True

    def DestroyWindow(self):
        # Window closed -> stop the server (no more draining possible)
        stop()


def open_panel(port=DEFAULT_PORT):
    """Starts the server and opens the window with the embedded frontend."""
    global _dialog
    port = start(port)
    # Instantiate freshly in case size/layout has changed.
    if _dialog is None or not _dialog.IsOpen():
        _dialog = ServerDialog(port)
        _dialog.Open(c4d.DLG_TYPE_ASYNC, pluginid=_SRV_DIALOG_ID,
                     defaultw=1200, defaulth=820)
    return port
