from __future__ import annotations

import sys

# The process singleton (HTTP server + main-thread queue + progress) lives in
# this package and must survive per-request hot reload. It now sits under
# ``cinema`` (the C4D host), so its ancestor packages are kept too — a kept
# submodule under a purged parent would be orphaned.
_KEEP_PACKAGE = "overseer.cinema.bridge"
_ANCESTORS = frozenset(
    ".".join(_KEEP_PACKAGE.split(".")[:i])
    for i in range(1, len(_KEEP_PACKAGE.split(".")))
)  # -> {"overseer", "overseer.cinema"}


def reload_all() -> int:
    dropped = 0
    for name in list(sys.modules):
        if name == "overseer" or not name.startswith("overseer."):
            continue
        if name in _ANCESTORS:
            continue
        if name == _KEEP_PACKAGE or name.startswith(_KEEP_PACKAGE + "."):
            continue
        del sys.modules[name]
        dropped += 1
    return dropped
