from __future__ import annotations

from overseer import updater
from overseer.blender import constants
from overseer.core import defaults


def test_blender_registers_its_port():
    # postcondition: the host owns its port; core carries no host values
    assert constants.DEFAULT_PORT == 8788
    assert not hasattr(defaults, "DEFAULT_PORT")
    assert not hasattr(defaults, "DEFAULT_PORT_BLENDER")


def test_blender_update_profile_fits_the_clean_update_target():
    # do it: the registered values must plug straight into core's UpdateTarget
    target = updater.UpdateTarget(
        repo=defaults.UPDATE_REPO, current_version="0.0.0",
        install_dir=".", data_dir=".", **constants.UPDATE_PROFILE)

    # postcondition
    assert target.asset_pattern == "Overseer-Blender-*.zip"
    assert target.payload_marker == "__init__.py"
    assert not hasattr(defaults, "UPDATE_BLENDER")
