# -*- coding: utf-8 -*-
"""
Scene Organizer  -  loader plugin

Registers ONLY two CommandData at startup (like any normal plugin ->
no startup risk, no MessageData anymore):
  * "Scene Organizer"        -> native GeDialog
  * "Scene Organizer (Web)"  -> starts local server + control dialog (whose
                                timer drains the request queue on the main thread)

Hot-reload: `sceneorg` is freshly loaded on every dialog invocation
(EXCEPTION: sceneorg.bridge = server/queue singleton). Only the initial
registration requires one restart.
"""

import os
import sys

import c4d

# Maxon-registered plugin ID (official, "GFCSceneOrganizer"): 1069217.
# The other globally registered elements derive from it as a contiguous
# block -> out of the shared dev range 1000001-1000010:
#   1069217  CommandData  "Scene Organizer"          (here: CMD_DIALOG)
#   1069218  async dialog pluginid (native dialog)   -> plugin_entry.py
#   1069219  CommandData  "Scene Organizer (Web)"    (here: CMD_WEB)
#   1069220  async ServerDialog pluginid             -> bridge.py
CMD_DIALOG = 1069217
CMD_WEB = 1069219
WEB_PORT = 8787


def _ensure_path():
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)


def _reload_sceneorg():
    _ensure_path()
    # do NOT purge bridge -> server/queue singleton is preserved
    for mod in [m for m in sys.modules
                if (m == "sceneorg" or m.startswith("sceneorg."))
                and m != "sceneorg.bridge"]:
        del sys.modules[mod]


class SceneOrganizerCommand(c4d.plugins.CommandData):
    def Execute(self, doc, *args, **kwargs):
        try:
            _reload_sceneorg()
            import sceneorg.plugin_entry as entry
            entry.execute(doc)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            print("[SceneOrganizer] ERROR:\n" + tb)
            c4d.gui.MessageDialog("Scene Organizer error:\n\n" + tb)
            return False
        return True


class SceneOrganizerWebCommand(c4d.plugins.CommandData):
    def Execute(self, doc, *args, **kwargs):
        try:
            _ensure_path()
            import sceneorg.bridge as bridge
            port = bridge.open_panel(WEB_PORT)
            print("[SceneOrganizer] Web UI running: http://127.0.0.1:%d/" % port)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            print("[SceneOrganizer] Web ERROR:\n" + tb)
            c4d.gui.MessageDialog("Scene Organizer Web error:\n\n" + tb)
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
        id=CMD_DIALOG, str="Scene Organizer", info=0,
        help="Analyzes and organizes the scene structure",
        dat=SceneOrganizerCommand(), icon=None), "Dialog-Command")
    _safe(lambda: c4d.plugins.RegisterCommandPlugin(
        id=CMD_WEB, str="Scene Organizer (Web)", info=0,
        help="Starts the web frontend (localhost)",
        dat=SceneOrganizerWebCommand(), icon=None), "Web-Command")
    print("[SceneOrganizer] registered (dialog %d, web %d)." % (CMD_DIALOG, CMD_WEB))


if __name__ == "__main__":
    main()
