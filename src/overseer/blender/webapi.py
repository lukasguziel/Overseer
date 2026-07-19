"""Blender JSON /api - a thin binding over the shared op layer.

All op logic lives in ``overseer.core.hostapi.webapi`` (host-neutral, written
against the ports). This module only binds the Blender ``HostContext`` into it.
Hot-reloaded per request like before, so edits to the shared layer or the
adapters take effect on the next API call.
"""
from __future__ import annotations

from ..core.hostapi.webapi import WebApi
from .context import BlenderContext

_api = WebApi(BlenderContext())

handle = _api.handle
invalidate_scene_cache = _api.invalidate_scene_cache
