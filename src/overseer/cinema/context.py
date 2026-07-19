"""CinemaContext - binds the Cinema 4D host into the shared op layer.

Implements ``HostContext``: the only c4d-specific surface the shared
``core.hostapi.webapi`` needs. All op logic is inherited from the shared webapi;
this carries over exactly the C4D behaviors the old ``cinema/webapi.py`` had
(prefs data dir + legacy folder rename, the dev-repo export mirror, the C4D
status bar, resource type icons, the native file/folder pickers).
"""
from __future__ import annotations

import base64
import importlib
import os
import tempfile

import c4d

from ..core import webio
from ..core.hostapi import HostContext
from . import bridge
from .adapter import SceneAdapter, load_journal, save_journal
from .scene_host import CDoc

# Repo/plugin root = dir containing the ``overseer`` package (3 up from here).
PLUGIN_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _prefs_base() -> str | None:
    try:
        return c4d.storage.GeGetC4DPath(c4d.C4D_PATH_PREFS)
    except Exception:
        return None


def _export_dir(data_dir: str) -> str:
    """The dev-repo report mirror: env override, then a ``dev_repo.txt`` stamp
    pointing at the source repo's ``var/``, else the data dir."""
    env = os.environ.get("OVERSEER_EXPORT_DIR")
    if env and os.path.isdir(env):
        return env
    try:
        stamp = os.path.join(PLUGIN_DIR, "dev_repo.txt")
        if os.path.isfile(stamp):
            with open(stamp, encoding="utf-8-sig") as f:
                repo = f.read().strip()
            if repo and os.path.isdir(repo):
                var = os.path.join(repo, "var")
                os.makedirs(var, exist_ok=True)
                return var
    except OSError:
        pass
    return data_dir


class CinemaContext(HostContext):

    def __init__(self) -> None:
        self._plugin_dir = PLUGIN_DIR
        self._data_dir = webio.resolve_data_dir(PLUGIN_DIR, _prefs_base())
        self._export_dir = _export_dir(self._data_dir)

    # -- document + adapter -------------------------------------------------
    def active_host(self):
        return CDoc.active()

    def make_adapter(self, host):
        return SceneAdapter(getattr(host, "raw", host))

    # -- paths --------------------------------------------------------------
    @property
    def plugin_dir(self) -> str:
        return self._plugin_dir

    @property
    def data_dir(self) -> str:
        return self._data_dir

    @property
    def export_dir(self) -> str:
        return self._export_dir

    # -- progress (bridge + C4D status bar) ---------------------------------
    def progress(self, phase, current=0, total=0, detail="") -> None:
        bridge.set_progress(phase, current, total, detail)
        try:
            c4d.StatusSetText("Overseer: %s" % phase)
            if total:
                c4d.StatusSetBar(int(current * 100 / max(1, total)))
            else:
                c4d.StatusSetSpin()
        except Exception:
            pass

    def clear_progress(self) -> None:
        bridge.clear_progress()
        try:
            c4d.StatusClear()
        except Exception:
            pass

    # -- bridge facades -----------------------------------------------------
    def server_port(self) -> int:
        fn = getattr(bridge, "server_port", None)
        return int(fn()) if fn else int(getattr(bridge, "DEFAULT_PORT", 8787))

    def lan_enabled(self) -> bool:
        return bool(getattr(bridge, "lan_enabled", lambda: False)())

    # -- journal ------------------------------------------------------------
    def load_journal(self, host, fallback_path: str) -> list:
        return load_journal(getattr(host, "raw", host), fallback_path)

    def save_journal(self, host, entries: list, fallback_path: str) -> None:
        save_journal(getattr(host, "raw", host), entries, fallback_path)

    # -- host-specific ops --------------------------------------------------
    def type_icons(self, ids) -> dict:
        import overseer
        cache = getattr(overseer, "_type_icons", None)
        if cache is None:
            cache = overseer._type_icons = {}
        tmp = os.path.join(tempfile.gettempdir(), "so_typeicon.png")
        icons: dict = {}
        for tid in ids or []:
            try:
                tid = int(tid)
            except (TypeError, ValueError):
                continue
            if tid not in cache:
                data = ""
                try:
                    bmp = c4d.bitmaps.InitResourceBitmap(tid)
                    if bmp is not None and bmp.GetSize()[0] > 0 \
                            and bmp.Save(tmp, c4d.FILTER_PNG) == c4d.IMAGERESULT_OK:
                        with open(tmp, "rb") as f:
                            data = ("data:image/png;base64,"
                                    + base64.b64encode(f.read()).decode("ascii"))
                except Exception:
                    data = ""
                cache[tid] = data
            if cache[tid]:
                icons[str(tid)] = cache[tid]
        try:
            os.remove(tmp)
        except OSError:
            pass
        return icons

    def pick_texture_path(self, payload: dict, host) -> dict:
        raw = str(payload.get("path") or "")
        doc = getattr(host, "raw", host)
        try:
            chosen = c4d.storage.LoadDialog(
                type=c4d.FILESELECTTYPE_IMAGES,
                title="Pick replacement for %s" % os.path.basename(raw),
                flags=c4d.FILESELECT_LOAD,
                def_path=doc.GetDocumentPath() or "")
        except Exception as ex:  # noqa: BLE001
            return {"error": "file dialog failed: %s" % ex}
        if not chosen:
            return {"cancelled": True}
        return {"picked": chosen}

    def pick_folder(self, payload: dict, host) -> dict:
        doc = getattr(host, "raw", host)
        try:
            chosen = c4d.storage.LoadDialog(
                type=c4d.FILESELECTTYPE_ANYTHING,
                title=str(payload.get("title") or "Pick a folder"),
                flags=c4d.FILESELECT_DIRECTORY,
                def_path=doc.GetDocumentPath() or "")
        except Exception as ex:  # noqa: BLE001
            return {"error": "folder dialog failed: %s" % ex}
        return {"ok": True, "path": chosen or "", "cancelled": not chosen}

    def audit(self, prefix: str):
        name = {"tags": "audit_tags", "gens": "audit_generators",
                "files": "audit_files", "sims": "audit_sims",
                "perf": "audit_perf"}.get(prefix)
        if name is None:
            return None
        return importlib.import_module("overseer.cinema." + name)
