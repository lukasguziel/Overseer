"""Overseer - Blender addon entry point.

Registers a single operator that starts the local web server and opens the
Overseer web UI in the browser (the same UI as the Cinema 4D build), plus a
sidebar panel button in the 3D Viewport. The bundled ``overseer`` Python
package (which contains the ``blender`` host glue, the shared ``core``/
``naming`` logic and ``config``) sits next to this file once deployed/zipped,
together with the ``web`` build and ``vendor`` (Pillow); we insert this folder
on ``sys.path`` so ``import overseer`` resolves the bundle.
"""
from __future__ import annotations

import os
import sys

bl_info = {
    "name": "Overseer",
    "author": "Lukas Guziel",
    "version": (1, 2, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N) > Overseer",
    "description": "Analyze & organize the scene: naming, collections, "
                   "materials, textures, modifiers, simulations, files. "
                   "Web UI shared with the Cinema 4D build.",
    "category": "Scene",
    "doc_url": "https://github.com/lukasguziel/overseer",
}

_ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
if _ADDON_DIR not in sys.path:
    sys.path.insert(0, _ADDON_DIR)

import bpy  # noqa: E402


class OVERSEER_OT_open(bpy.types.Operator):
    bl_idname = "overseer.open"
    bl_label = "Open Overseer"
    bl_description = "Start the Overseer server and open the web UI"

    def execute(self, context):
        try:
            import overseer.blender.host as host
            port = host.open_panel()
            self.report({"INFO"},
                        "Overseer running: http://127.0.0.1:%d/" % port)
        except Exception as ex:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            self.report({"ERROR"}, "Overseer failed to start: %s" % ex)
            return {"CANCELLED"}
        return {"FINISHED"}


class OVERSEER_PT_panel(bpy.types.Panel):
    bl_label = "Overseer"
    bl_idname = "OVERSEER_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Overseer"

    def draw(self, context):
        layout = self.layout
        layout.operator("overseer.open", icon="WORLD")
        running = False
        try:
            import overseer.blender.host as host
            running = host.is_running()
        except Exception:
            running = False
        if running:
            try:
                port = host.server_port()
            except Exception:
                port = 8788
            layout.label(text="Running on :%d" % port, icon="CHECKMARK")


_CLASSES = (OVERSEER_OT_open, OVERSEER_PT_panel)


def _update_boot_guard():
    # If a freshly installed update never got confirmed, restore its backup
    # (see docs/overseer/updater.md); pure imports only, safe at register time.
    try:
        from overseer import __version__, updater
        from overseer.blender.context import BlenderContext
        from overseer.core import defaults
        ctx = BlenderContext()
        updater.note_boot(updater.UpdateTarget(
            repo=defaults.UPDATE_REPO, current_version=__version__,
            install_dir=ctx.plugin_dir, data_dir=ctx.data_dir,
            **defaults.UPDATE_BLENDER))
    except Exception:
        import traceback
        traceback.print_exc()


def register():
    _update_boot_guard()
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
    # Full teardown: stop the server AND drop the timer + depsgraph handlers so
    # a disabled addon leaves nothing firing (the audit flagged the orphaned
    # persistent pump timer).
    try:
        import overseer.blender.host as host
        host.shutdown()
    except Exception:
        pass


if __name__ == "__main__":
    register()
