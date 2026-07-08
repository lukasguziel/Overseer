# plugin_entry.py

Entry point called by the `.pyp` loader (c4d-dependent); opens the native dialog.

- `_DIALOG` — module-level global that keeps the dialog alive across calls (must survive as modal/non-modal state).
- `execute(doc)` — lazily creates `SceneOrganizerDialog` and opens it async so C4D stays usable. Uses dialog plugin id `1069218` (distinct from the command id `1069217`, for dock/restore; derived from the Maxon base ID).
