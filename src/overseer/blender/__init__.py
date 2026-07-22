"""overseer.blender - Blender host glue (the Blender twin of overseer.cinema).

Only this package imports ``bpy`` (never loaded by tests, exactly like
``overseer.cinema`` never loads ``c4d`` in tests). Everything under ``core/``,
plus ``config.py`` and the whole web frontend are shared verbatim
with the Cinema 4D build; this package answers the identical JSON /api contract
against a Blender scene.

See docs/ai/blender.md for the C4D -> Blender concept mapping and the adapter
contract. ``host``/``pump``/``server``/``reload`` are the process singleton and
are excluded from per-request hot reload; every other submodule
(``webapi``, the per-area modules, ``scene.*``) is re-imported per request.
"""
