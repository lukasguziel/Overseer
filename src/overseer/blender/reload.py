"""Per-request hot reload for the Blender backend.

Mirrors ``overseer.bridge.reload`` but keeps the Blender process-singleton
modules alive (host/pump/server/reload/scene) while purging every other
``overseer.*`` module so the next request re-imports edited ``webapi`` /
adapter / audit source with no Blender restart.
"""
from __future__ import annotations

import sys

# Modules that hold live server/queue/timer state (or are imported by them on
# the main thread) must never be purged, or the running server would lose its
# backing objects mid-session.
_KEEP = (
    "overseer.blender.host",
    "overseer.blender.pump",
    "overseer.blender.server",
    "overseer.blender.reload",
    "overseer.blender.scene",
)


def _keep(name: str) -> bool:
    if name == "overseer" or name == "overseer.blender":
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
