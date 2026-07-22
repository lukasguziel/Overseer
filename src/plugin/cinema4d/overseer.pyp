import os
import sys

import c4d

CMD_MAIN = 1069217


def _ensure_path():
    base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)


def _update_target():
    _ensure_path()
    from overseer import __version__, updater
    from overseer.cinema.constants import UPDATE_PROFILE
    from overseer.core import defaults, webio
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        prefs = c4d.storage.GeGetC4DPath(c4d.C4D_PATH_PREFS)
    except Exception:
        prefs = None
    return updater.UpdateTarget(
        repo=defaults.UPDATE_REPO, current_version=__version__,
        install_dir=base, data_dir=webio.resolve_data_dir(base, prefs),
        **UPDATE_PROFILE)


def _update_boot_guard():
    from overseer import updater
    state = updater.note_boot(_update_target())
    if state and state.get("state") == "rolled_back":
        print("[Overseer] The update to v%s never started successfully - "
              "restored v%s from its backup."
              % (state.get("to"), state.get("from")))


def _update_failed_start():
    try:
        from overseer import updater
        state = updater.failed_start(_update_target())
        if state and state.get("state") == "rolled_back":
            return ("\n\nA freshly installed update failed to start, so the "
                    "previous version v%s was restored from its backup.\n"
                    "Please restart Cinema 4D." % state.get("from"))
    except Exception:
        pass
    return ""


def _load_icon():
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "logo.png")
        src = c4d.bitmaps.BaseBitmap()
        if src.InitWith(path)[0] != c4d.IMAGERESULT_OK:
            return None
        icon = c4d.bitmaps.BaseBitmap()
        icon.Init(32, 32)
        src.ScaleIt(icon, 256, True, False)
        return icon
    except Exception:
        return None


class OverseerCommand(c4d.plugins.CommandData):
    def Execute(self, doc, *args, **kwargs):
        try:
            _ensure_path()
            import overseer.cinema.bridge as bridge
            port = bridge.open_panel()
            print("[Overseer] Web UI running: http://127.0.0.1:%d/" % port)
        except Exception:
            import traceback
            tb = traceback.format_exc()
            print("[Overseer] ERROR:\n" + tb)
            c4d.gui.MessageDialog("Overseer error:\n\n" + tb
                                  + _update_failed_start())
            return False
        return True


def _safe(fn, what):
    try:
        fn()
    except Exception:
        import traceback
        print("[Overseer] Registration '%s' failed:\n%s"
              % (what, traceback.format_exc()))


def main():
    _safe(_update_boot_guard, "UpdateGuard")
    _safe(lambda: c4d.plugins.RegisterCommandPlugin(
        id=CMD_MAIN, str="Overseer", info=0,
        help="Analyzes and organizes the scene structure",
        dat=OverseerCommand(), icon=_load_icon()), "Command")
    print("[Overseer] registered (%d)." % CMD_MAIN)


if __name__ == "__main__":
    main()
