from __future__ import annotations

import os
import sys

VENDOR_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor")


def vendor_dir() -> str:
    return VENDOR_DIR


def available() -> bool:
    return os.path.isdir(VENDOR_DIR)


def ensure_path(path: str | None = None) -> bool:
    target = path or VENDOR_DIR
    if not os.path.isdir(target):
        return False
    if target not in sys.path:
        sys.path.append(target)
    return True


def import_pillow():
    ensure_path()
    try:
        from PIL import Image
        return Image
    except Exception:
        return None
