from __future__ import annotations

import webbrowser

import c4d

SERVER_DIALOG_ID = 1069220


class ServerDialog(c4d.gui.GeDialog):

    _BTN_OPEN = 3001
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
        self.GroupBegin(1000, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, rows=2)
        self.GroupBorderSpace(6, 6, 6, 6)

        # Escape hatch: the embedded HtmlViewer misbehaves on some C4D
        # versions (resize collapses the window) — the same UI always works
        # in the default browser against the same local server.
        self.GroupBegin(1001, c4d.BFH_SCALEFIT, cols=2, rows=1)
        self.AddButton(self._BTN_OPEN, c4d.BFH_LEFT, name="Open in Browser")
        self.AddStaticText(
            0, c4d.BFH_SCALEFIT,
            name="Window acting up? Use the browser — same UI, same server.")
        self.GroupEnd()

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
        if cid == self._BTN_OPEN:
            webbrowser.open(self._url())
        elif cid == self._BTN_RELOAD:
            self._load()
        elif cid == self._BTN_STOP:
            self.Close()
        return True

    def DestroyWindow(self):
        self._server.stop()
