# -*- coding: utf-8 -*-
"""
Scene Organizer  -  loader plugin

Registers ONE CommandData at startup (like any normal plugin -> no startup
risk, no MessageData anymore, no submenu -> a single click launches it):
  * "Scene Organizer"  -> starts local server + control dialog (whose timer
                          drains the request queue on the main thread) and
                          opens the web frontend.

Hot-reload: `sceneorg.webapi` is freshly loaded on every web request
(EXCEPTION: sceneorg.bridge = server/queue singleton). Only the initial
registration requires one restart.
"""

import os
import sys

import c4d

# Maxon-registered plugin ID (official, "GFCSceneOrganizer"): 1069217.
# The other globally registered elements derive from it as a contiguous
# block -> out of the shared dev range 1000001-1000010:
#   1069217  CommandData  "Scene Organizer"          (here: CMD_MAIN)
#   1069220  async ServerDialog pluginid             -> bridge.py
CMD_MAIN = 1069217
WEB_PORT = 8787


def _ensure_path():
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)


def _load_icon():
    """Load so_logo.jpg (next to this .pyp) as a 32x32 command icon.

    Returns None on any failure so registration never breaks over the icon.
    """
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "so_logo.jpg")
        src = c4d.bitmaps.BaseBitmap()
        if src.InitWith(path)[0] != c4d.IMAGERESULT_OK:
            return None
        icon = c4d.bitmaps.BaseBitmap()
        icon.Init(32, 32)
        src.ScaleIt(icon, 256, True, False)
        return icon
    except Exception:
        return None


class SceneOrganizerCommand(c4d.plugins.CommandData):
    def Execute(self, doc, *args, **kwargs):
        try:
            _ensure_path()
            import sceneorg.bridge as bridge
            port = bridge.open_panel(WEB_PORT)
            print("[SceneOrganizer] Web UI running: http://127.0.0.1:%d/" % port)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            print("[SceneOrganizer] ERROR:\n" + tb)
            c4d.gui.MessageDialog("Scene Organizer error:\n\n" + tb)
            return False
        return True


def _safe(fn, what):
    try:
        fn()
    except Exception:
        import traceback
        print("[SceneOrganizer] Registration '%s' failed:\n%s"
              % (what, traceback.format_exc()))


def main():
    _safe(lambda: c4d.plugins.RegisterCommandPlugin(
        id=CMD_MAIN, str="Scene Organizer", info=0,
        help="Analyzes and organizes the scene structure",
        dat=SceneOrganizerCommand(), icon=_load_icon()), "Command")
    print("[SceneOrganizer] registered (%d)." % CMD_MAIN)


if __name__ == "__main__":
    main()
