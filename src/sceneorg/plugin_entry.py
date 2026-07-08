from __future__ import annotations

import c4d

from .cinema.dialog import SceneOrganizerDialog

_DIALOG = None


def execute(doc):
    global _DIALOG
    if _DIALOG is None:
        _DIALOG = SceneOrganizerDialog()
    _DIALOG.Open(c4d.DLG_TYPE_ASYNC, pluginid=1069218, defaultw=600, defaulth=460)
    return True
