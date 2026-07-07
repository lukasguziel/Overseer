"""Einstiegspunkt, den der .pyp-Loader aufruft (c4d-abhaengig)."""

from __future__ import annotations

import c4d

from .dialog import SceneOrganizerDialog

# Der Dialog muss als modaler/nicht-modaler Zustand ueberleben.
_DIALOG = None


def execute(doc):
    global _DIALOG
    if _DIALOG is None:
        _DIALOG = SceneOrganizerDialog()
    # Async, damit C4D bedienbar bleibt; eigene Dialog-ID (getrennt von der
    # Command-ID 1000001) fuer Dock/Restore.
    _DIALOG.Open(c4d.DLG_TYPE_ASYNC, pluginid=1000002, defaultw=600, defaulth=460)
    return True
