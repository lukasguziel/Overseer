"""Entry point called by the .pyp loader (c4d-dependent)."""

from __future__ import annotations

import c4d

from .cinema.dialog import SceneOrganizerDialog

# The dialog must survive as modal/non-modal state.
_DIALOG = None


def execute(doc):
    global _DIALOG
    if _DIALOG is None:
        _DIALOG = SceneOrganizerDialog()
    # Async so C4D stays usable; separate dialog ID (distinct from the
    # command ID 1069217) for dock/restore. Derived from the Maxon base ID.
    _DIALOG.Open(c4d.DLG_TYPE_ASYNC, pluginid=1069218, defaultw=600, defaulth=460)
    return True
