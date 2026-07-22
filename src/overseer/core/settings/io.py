"""Per-project UI state persistence (host-neutral file IO).

Pure: no host SDK. Stores each project's web-UI state under
``<data_dir>/configs/<slug>.json`` (slug/sanitize delegated to
``settings.logic``). Shared by every host via the hostapi webapi. (Moved out
of the host packages so the shared ``core`` layer stays host-agnostic.)
"""
from __future__ import annotations

import json
import os
import time

from . import logic

# The global (all-projects) ui profile file. Project slugs always start with
# an alphanumeric character, so the underscore name cannot collide.
GLOBAL_SLUG = "_global"


def _configs_dir(data_dir: str) -> str:
    path = os.path.join(data_dir, "configs")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def _config_path(data_dir: str, slug: str) -> str:
    return os.path.join(_configs_dir(data_dir), slug + ".json")


def _read_ui_file(fp: str) -> dict:
    if not os.path.isfile(fp):
        return {}
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    ui = data.get("ui")
    return ui if isinstance(ui, dict) else {}


def _write_ui_file(fp: str, payload: dict) -> bool:
    tmp = fp + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp, fp)
    except Exception:
        try:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception:
            return False
    return True


def load_ui(data_dir: str, path: str, name: str) -> dict:
    slug = logic.project_slug(path, name)
    if not slug:
        return {}
    return logic.sanitize_ui(_read_ui_file(_config_path(data_dir, slug)))


def save_ui(data_dir: str, path: str, name: str, ui: object) -> dict:
    slug = logic.project_slug(path, name)
    if not slug:
        return {"ok": False, "error": "unsaved document"}
    payload = {
        "schema": 1,
        "project": {"path": path or "", "name": name or ""},
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ui": logic.sanitize_ui(ui),
    }
    fp = _config_path(data_dir, slug)
    if not _write_ui_file(fp, payload):
        return {"ok": False, "error": "write failed"}
    return {"ok": True, "path": fp, "slug": slug}


def load_global_ui(data_dir: str) -> dict:
    return logic.sanitize_global_ui(
        _read_ui_file(_config_path(data_dir, GLOBAL_SLUG)))


def save_global_ui(data_dir: str, ui: object) -> dict:
    payload = {
        "schema": 1,
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ui": logic.sanitize_global_ui(ui),
    }
    fp = _config_path(data_dir, GLOBAL_SLUG)
    if not _write_ui_file(fp, payload):
        return {"ok": False, "error": "write failed"}
    return {"ok": True, "path": fp}
