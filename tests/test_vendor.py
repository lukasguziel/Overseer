import os
import sys

from sceneorg import vendor


def test_vendor_dir_sits_next_to_the_package():
    # .../src/vendor, i.e. a sibling of .../src/sceneorg
    parent = os.path.dirname(vendor.vendor_dir())
    assert os.path.isdir(os.path.join(parent, "sceneorg"))
    assert os.path.basename(vendor.vendor_dir()) == "vendor"


def test_missing_vendor_dir_is_not_an_error(tmp_path):
    # A checkout without the bundled wheels must still run.
    assert vendor.ensure_path(str(tmp_path / "nope")) is False


def test_ensure_path_appends_once(tmp_path):
    target = tmp_path / "vendor"
    target.mkdir()
    before = list(sys.path)
    try:
        assert vendor.ensure_path(str(target)) is True
        assert vendor.ensure_path(str(target)) is True
        assert sys.path.count(str(target)) == 1
        # Appended, not prepended: a user-installed package still wins.
        assert sys.path[-1] == str(target)
    finally:
        sys.path[:] = before


def test_import_pillow_returns_none_or_a_module():
    # CI has no bundled wheels; either way this must never raise.
    mod = vendor.import_pillow()
    assert mod is None or hasattr(mod, "open")
