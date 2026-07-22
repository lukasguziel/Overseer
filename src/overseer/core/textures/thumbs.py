"""Pillow-rendered texture thumbnails, host-independent.

The web UI shows a tiny square preview per texture row. Rendering those with
the host's bitmap engine forces every request through the host main thread
(the host bridges queue all API calls there), and a big map blocks that
thread for around a second — swallowing clicks in the embedded web view. The common
formats are therefore decoded with the vendored Pillow, which is safe on any
thread: a host bridge can answer them straight from the server thread, and the
shared op layer uses the same path before falling back to the host bitmap
engine (EXR/HDR and renderer-specific containers).
"""
from __future__ import annotations

import base64
import io
import os

# Formats the vendored Pillow decodes reliably. Everything else returns None
# and stays on the host bitmap engine.
_PILLOW_EXTS = {
    ".png", ".jpg", ".jpeg", ".jfif", ".bmp", ".gif", ".tif", ".tiff",
    ".webp", ".tga", ".ico",
}


def supported(path: str) -> bool:
    return os.path.splitext(path or "")[1].lower() in _PILLOW_EXTS


def thumbnail(path: str, size: int = 40) -> str | None:
    """Square PNG thumbnail as a data URI, or None.

    None means "let the host bitmap engine try": missing file, Pillow not
    vendored, unsupported extension or a decode error. Matches the host
    engines' look — squashed to size x size like the host bitmap engines do.
    """
    if not supported(path) or not os.path.isfile(path):
        return None
    from ...vendor import import_pillow
    image_mod = import_pillow()
    if image_mod is None:
        return None
    try:
        with image_mod.open(path) as im:
            im = im.convert("RGBA")
            im = im.resize((size, size))
            buf = io.BytesIO()
            im.save(buf, format="PNG")
        data = base64.b64encode(buf.getvalue()).decode("ascii")
        return "data:image/png;base64," + data
    except Exception:
        return None
