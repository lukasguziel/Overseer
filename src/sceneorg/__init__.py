"""
sceneorg - reine, C4D-unabhaengige Domaenenlogik fuer den Scene Organizer.

WICHTIG: Dieses Package darf NICHT `c4d` importieren, damit es in CI
(GitHub Actions) ohne Cinema 4D getestet werden kann. Alles C4D-spezifische
lebt ausschliesslich in `c4d_adapter`, `plugin_entry` und `dialog` -- diese
werden von den Tests nie importiert.
"""

__version__ = "0.1.0"
