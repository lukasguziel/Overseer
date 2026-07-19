"""Cinema 4D JSON /api - a thin binding over the shared op layer.

All op logic lives in ``overseer.core.hostapi.webapi`` (host-neutral, written
against the ports). This module only binds the C4D ``HostContext`` into it.
Re-imported per request by the bridge's ``reload_all()``, so edits to the shared
layer or the c4d adapters take effect on the next API call.

(Was a ~1400-line copy of the op registry; that logic now lives once in the
shared webapi. See docs/ai/hostapi.md.)
"""
from __future__ import annotations

from ..core.hostapi.webapi import WebApi
from .context import CinemaContext

_api = WebApi(CinemaContext())

handle = _api.handle
invalidate_scene_cache = _api.invalidate_scene_cache
