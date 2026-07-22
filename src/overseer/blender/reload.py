"""Per-request hot reload for the Blender backend.

Mirrors ``overseer.cinema.bridge.reload`` but keeps the Blender process-singleton
modules alive (host/pump/server/reload plus the ``BScene`` doc wrapper in
``scene.doc``) while purging every other ``overseer.*`` module so the next
request re-imports edited ``webapi`` / area source with no Blender restart.
"""
from __future__ import annotations

import sys

# Modules that hold live server/queue/timer state (or are imported by them on
# the main thread) must never be purged, or the running server would lose its
# backing objects mid-session. ``scene.doc`` (BScene) is kept so cached doc
# wrappers keep their class identity; the rest of ``scene`` (adapter/readers)
# hot-reloads like every area module.
_KEEP = (
    "overseer.blender.host",
    "overseer.blender.pump",
    "overseer.blender.server",
    "overseer.blender.reload",
    "overseer.blender.scene.doc",
)

# Kept exactly (not by prefix): ancestor packages of kept submodules — a kept
# submodule under a purged parent would be orphaned.
_KEEP_EXACT = ("overseer", "overseer.blender", "overseer.blender.scene")


def _keep(name: str) -> bool:
    if name in _KEEP_EXACT:
        return True
    for base in _KEEP:
        if name == base or name.startswith(base + "."):
            return True
    return False


def reload_all() -> int:
    dropped = 0
    for name in list(sys.modules):
        if name != "overseer" and not name.startswith("overseer."):
            continue
        if _keep(name):
            continue
        del sys.modules[name]
        dropped += 1
    return dropped
