"""Make the bundled third-party packages importable.

`src/vendor/` holds packages we ship with the plugin (currently Pillow, for
high-quality texture resampling) so the artist never has to pip-install
anything into Cinema's Python. The directory is OPTIONAL: a checkout without
it still runs — every caller must degrade gracefully.

Pure stdlib, no `c4d` — the path juggling is testable in CI.
"""
from __future__ import annotations

import os
import sys

# .../src/overseer/vendor.py -> .../src/vendor
VENDOR_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor")


def vendor_dir() -> str:
    return VENDOR_DIR


def available() -> bool:
    return os.path.isdir(VENDOR_DIR)


def ensure_path(path: str | None = None) -> bool:
    """Put the vendor dir on sys.path (once). True if it is there now.

    Appended, never prepended: a package the user installed into Cinema's
    Python themselves wins over our bundled copy — their machine, their call.
    """
    target = path or VENDOR_DIR
    if not os.path.isdir(target):
        return False
    if target not in sys.path:
        sys.path.append(target)
    return True


def import_pillow():
    """The Pillow Image module, or None if it is not available anywhere."""
    ensure_path()
    try:
        from PIL import Image
        return Image
    except Exception:
        return None
