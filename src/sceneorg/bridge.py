"""HTTP-Bruecke fuer das Web-Frontend (c4d-abhaengig).

Wichtig: Dokument-Zugriffe MUESSEN auf dem Main-Thread laufen. Der HTTP-Server
laeuft auf einem Hintergrund-Thread und legt jede Anfrage in eine Queue; ein
MessageData-Plugin (im .pyp registriert) leert die Queue via SpecialEventAdd
auf dem Main-Thread und ruft `webapi.handle` auf.

Dieses Modul ist ein prozessweiter Singleton (Queue + Serverzustand) und wird
vom Loader ABSICHTLICH NICHT hot-reloaded -- sonst ginge die Queue verloren.
Die eigentliche API-Logik (`webapi`) wird bei jedem Drain frisch geladen.
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
_SRV_DIALOG_ID = 1000006
WEB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

_server = None
_thread = None
_queue: queue.Queue = queue.Queue()

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
    """Vom Server-Thread: Anfrage einreihen und auf das Ergebnis warten.

    Das Abarbeiten passiert auf dem Main-Thread ueber den Timer des
    ServerDialog (siehe unten) -> KEINE MessageData/SpecialEventAdd noetig,
    daher kein Startup-Risiko.
    """
    req = _Request(payload)
    _queue.put(req)
    if not req.event.wait(timeout):
        raise TimeoutError("Main-thread timeout (keep the server dialog open)")
    if req.error:
        raise RuntimeError(req.error)
    return req.result


def drain():
    """Auf dem MAIN-Thread (aus MessageData.CoreMessage): Queue abarbeiten."""
    while True:
        try:
            req = _queue.get_nowait()
        except queue.Empty:
            return
        try:
            from . import webapi
            importlib.reload(webapi)  # Hot-Reload der API-Logik
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
            self._json(submit(payload))
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _static(self):
        path = self.path.split("?")[0]
        if path in ("/", ""):
            path = "/index.html"
        full = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            # SPA-Fallback auf index.html
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
# Server-Kontroll-Dialog: draint die Queue per Timer auf dem Main-Thread.
# Solange dieses Fenster offen ist, werden Web-Requests bearbeitet.
# --------------------------------------------------------------------------

_BTN_OPEN = 3001
_BTN_STOP = 3002
_BTN_RELOAD = 3003
_ID_HTMLVIEW = 3010
_dialog = None


class ServerDialog(c4d.gui.GeDialog):
    """Kontroll-Dialog MIT eingebettetem Web-Frontend.

    Das React-Bundle wird nicht im externen Browser, sondern direkt IN diesem
    C4D-Fenster gerendert -- ueber das native CUSTOMGUI_HTMLVIEWER-Gadget
    (QtWebEngine). Der Viewer zeigt auf http://127.0.0.1:<port>/, also die
    gleiche Origin, die auch die App + /api/* ausliefert -> `fetch('/api/..')`
    im Frontend laeuft same-origin, kein CORS, kein file://-Mixed-Content.

    Faellt CUSTOMGUI_HTMLVIEWER weg (aeltere C4D-Builds), bleibt der klassische
    Browser-Button als Rueckfallebene.
    """

    def __init__(self, port):
        super().__init__()
        self._port = port
        self._html_gui = None

    def _url(self):
        return "http://127.0.0.1:%d/" % self._port

    def CreateLayout(self):
        self.SetTitle("Scene Organizer")
        # Nur der Viewer, fuellt das ganze Fenster. Debug-Aktionen (Reload/Open/
        # Stop) leben im Web-UI unter Misc -> Debug; Fenster schliessen stoppt
        # den Server (siehe DestroyWindow).
        self.GroupBegin(1000, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, rows=1)
        self.GroupBorderSpace(6, 6, 6, 6)

        html_constant = getattr(c4d, "CUSTOMGUI_HTMLVIEWER", None)
        if html_constant is None:
            # Kein eingebetteter Viewer -> im externen Browser oeffnen.
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
        self.SetTimer(100)  # ms -> Timer() draint die Queue auf dem Main-Thread
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
        # Fenster zu -> Server stoppen (kein Draining mehr moeglich)
        stop()


def open_panel(port=DEFAULT_PORT):
    """Startet den Server und oeffnet das Fenster mit eingebettetem Frontend."""
    global _dialog
    port = start(port)
    # Frisch instanziieren, falls sich Groesse/Layout geaendert hat.
    if _dialog is None or not _dialog.IsOpen():
        _dialog = ServerDialog(port)
        _dialog.Open(c4d.DLG_TYPE_ASYNC, pluginid=_SRV_DIALOG_ID,
                     defaultw=1200, defaulth=820)
    return port
