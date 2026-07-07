# -*- coding: utf-8 -*-
"""
Scene Organizer  -  Loader-Plugin

Registriert beim Start NUR zwei CommandData (wie jedes normale Plugin ->
kein Startup-Risiko, keine MessageData mehr):
  * "Scene Organizer"        -> nativer GeDialog
  * "Scene Organizer (Web)"  -> startet lokalen Server + Kontroll-Dialog (dessen
                                Timer die Request-Queue auf dem Main-Thread draint)

Hot-Reload: `sceneorg` wird bei jedem Dialog-Aufruf frisch geladen
(AUSNAHME: sceneorg.bridge = Server/Queue-Singleton). Nur die Erst-
Registrierung braucht 1x Neustart.
"""

import os
import sys

import c4d

CMD_DIALOG = 1000001
CMD_WEB = 1000005
WEB_PORT = 8787


def _ensure_path():
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)


def _reload_sceneorg():
    _ensure_path()
    # bridge NICHT purgen -> Server/Queue-Singleton bleibt erhalten
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
            print("[SceneOrganizer] FEHLER:\n" + tb)
            c4d.gui.MessageDialog("Scene Organizer error:\n\n" + tb)
            return False
        return True


class SceneOrganizerWebCommand(c4d.plugins.CommandData):
    def Execute(self, doc, *args, **kwargs):
        try:
            _ensure_path()
            import sceneorg.bridge as bridge
            port = bridge.open_panel(WEB_PORT)
            print("[SceneOrganizer] Web-UI laeuft: http://127.0.0.1:%d/" % port)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            print("[SceneOrganizer] Web-FEHLER:\n" + tb)
            c4d.gui.MessageDialog("Scene Organizer Web error:\n\n" + tb)
            return False
        return True


def _safe(fn, what):
    try:
        fn()
    except Exception:
        import traceback
        print("[SceneOrganizer] Registrierung '%s' fehlgeschlagen:\n%s"
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
    print("[SceneOrganizer] registriert (Dialog %d, Web %d)." % (CMD_DIALOG, CMD_WEB))


if __name__ == "__main__":
    main()
