from __future__ import annotations

import json
import os
import time

from ..core import ui_settings_logic as logic


def _configs_dir(data_dir: str) -> str:
    path = os.path.join(data_dir, "configs")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def _config_path(data_dir: str, slug: str) -> str:
    return os.path.join(_configs_dir(data_dir), slug + ".json")


def load_ui(data_dir: str, path: str, name: str) -> dict:
    slug = logic.project_slug(path, name)
    if not slug:
        return {}
    fp = _config_path(data_dir, slug)
    if not os.path.isfile(fp):
        return {}
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    return logic.sanitize_ui(data.get("ui"))


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
            return {"ok": False, "error": "write failed"}
    return {"ok": True, "path": fp, "slug": slug}
