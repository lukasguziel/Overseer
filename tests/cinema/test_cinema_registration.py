from __future__ import annotations

import ast
import pathlib

from overseer import updater
from overseer.core import defaults

CONSTANTS = (pathlib.Path(__file__).resolve().parents[2]
             / "src" / "overseer" / "cinema" / "constants.py")


def _module_constant(name: str):
    tree = ast.parse(CONSTANTS.read_text(encoding="utf-8"), str(CONSTANTS))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    return ast.literal_eval(node.value)
    raise AssertionError("constant %s not found in cinema/constants.py" % name)


def test_cinema_registers_its_port():
    # do it: cinema/constants.py imports c4d, so read the value via ast
    port = _module_constant("DEFAULT_PORT")

    # postcondition: the host owns its port; core carries no host values
    assert port == 8787
    assert not hasattr(defaults, "DEFAULT_PORT")


def test_cinema_update_profile_fits_the_clean_update_target():
    # setup
    profile = _module_constant("UPDATE_PROFILE")

    # do it: the registered values must plug straight into core's UpdateTarget
    target = updater.UpdateTarget(
        repo=defaults.UPDATE_REPO, current_version="0.0.0",
        install_dir=".", data_dir=".", **profile)

    # postcondition
    assert target.asset_pattern == "Overseer-Cinema4D-*.zip"
    assert target.payload_marker == "overseer.pyp"
    assert not hasattr(defaults, "UPDATE_CINEMA")
