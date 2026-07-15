from __future__ import annotations

import sys

_KEEP_PACKAGE = "overseer.bridge"


def reload_all() -> int:
    dropped = 0
    for name in list(sys.modules):
        if name == "overseer" or not name.startswith("overseer."):
            continue
        if name == _KEEP_PACKAGE or name.startswith(_KEEP_PACKAGE + "."):
            continue
        del sys.modules[name]
        dropped += 1
    return dropped
