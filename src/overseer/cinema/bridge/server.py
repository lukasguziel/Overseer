from __future__ import annotations

import http.server
import json
import os
import threading

import c4d

from ...core.defaults import DEFAULT_PORT

# web/ sits NEXT TO the overseer package in the plugin dir. This file is
# nested one level deeper than the blender host (cinema/bridge/ vs blender/),
# so it climbs FOUR levels: bridge -> cinema -> overseer package -> plugin dir.
WEB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))),
    "web")

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript",
    ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml",
    ".ico": "image/x-icon", ".png": "image/png", ".woff2": "font/woff2",
    ".map": "application/json",
}


class RequestHandler(http.server.BaseHTTPRequestHandler):

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
                return self._json(self.server.progress.snapshot())
            self._json(self.server.requests.submit(payload))
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _static(self):
        path = self.path.split("?")[0]
        if path in ("/", ""):
            path = "/index.html"
        full = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
        if not full.startswith(WEB_DIR) or not os.path.isfile(full):
            full = os.path.join(WEB_DIR, "index.html")
            if not os.path.isfile(full):
                self.send_response(404)
                self.end_headers()
                return
        ctype = CONTENT_TYPES.get(os.path.splitext(full)[1].lower(),
                                  "application/octet-stream")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class BridgeServer:

    def __init__(self, progress, requests):
        self._progress = progress
        self._requests = requests
        self._server = None
        self._thread = None
        self._lan = False
        self._port = DEFAULT_PORT

    @property
    def port(self) -> int:
        return self._port

    @property
    def lan_enabled(self) -> bool:
        return self._lan

    @property
    def is_running(self) -> bool:
        return self._server is not None

    def start(self, port=None) -> int:
        if self._server is not None:
            return self._port

        self._lan, config_port = self._config_settings()
        self._port = int(port or config_port)
        host = "0.0.0.0" if self._lan else "127.0.0.1"
        self._server = http.server.ThreadingHTTPServer((host, self._port),
                                                       RequestHandler)
        self._server.progress = self._progress
        self._server.requests = self._requests
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        daemon=True)
        self._thread.start()
        return self._port

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            self._thread = None

    @staticmethod
    def _config_candidates() -> list:
        paths = [os.path.join(os.path.dirname(WEB_DIR), "config.json")]
        try:
            base = c4d.storage.GeGetC4DPath(c4d.C4D_PATH_PREFS)
        except Exception:
            base = None
        if base:
            paths.insert(0, os.path.join(base, "scene_organizer", "config.json"))
            paths.insert(0, os.path.join(base, "overseer", "config.json"))
        return paths

    @classmethod
    def _config_settings(cls) -> tuple:
        for path in cls._config_candidates():
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            try:
                port = int(data.get("port") or DEFAULT_PORT)
            except (TypeError, ValueError):
                port = DEFAULT_PORT
            return bool(data.get("listen_lan", False)), port
        return False, DEFAULT_PORT
