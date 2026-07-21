from __future__ import annotations

import webbrowser

import c4d

SERVER_DIALOG_ID = 1069220


class ServerDialog(c4d.gui.GeDialog):

    _BTN_STOP = 3002
    _BTN_RELOAD = 3003
    _ID_HTMLVIEW = 3010

    def __init__(self, port, requests, server):
        super().__init__()
        self._port = port
        self._requests = requests
        self._server = server
        self._html_gui = None

    def _url(self):
        return "http://127.0.0.1:%d/" % self._port

    def CreateLayout(self):
        self.SetTitle("Overseer")
        self.GroupBegin(1000, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, rows=1)
        self.GroupBorderSpace(6, 6, 6, 6)

        # The browser escape hatch lives in the web UI itself (Misc > "Open in
        # browser" -> the shared open_browser op) — no native button here.
        html_constant = getattr(c4d, "CUSTOMGUI_HTMLVIEWER", None)
        if html_constant is None:
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
                self._ID_HTMLVIEW, html_constant, "",
                c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, 1180, 760, settings)
        self.GroupEnd()
        return True

    def InitValues(self):
        self.SetTimer(25)
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
        self._requests.drain()

    def Command(self, cid, msg):
        if cid == self._BTN_RELOAD:
            self._load()
        elif cid == self._BTN_STOP:
            self.Close()
        return True

    def DestroyWindow(self):
        self._server.stop()
