"""
sceneorg - pure, C4D-independent domain logic for the Scene Organizer.

IMPORTANT: This package must NOT import `c4d`, so it can be tested in CI
(GitHub Actions) without Cinema 4D. Everything C4D-specific lives exclusively
in `c4d_adapter`, `plugin_entry` and `dialog` -- these are never imported by
the tests.
"""

__version__ = "0.1.0"
