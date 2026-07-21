import json
import os
import zipfile

from overseer import updater

RELEASES = [
    {"tag_name": "v1.3.0", "name": "v1.3.0", "body": "## New\n- three",
     "published_at": "2026-07-20T10:00:00Z",
     "assets": [
         {"name": "Overseer-Blender-v1.3.0.zip",
          "browser_download_url": "https://x/bl.zip"},
         {"name": "Overseer-Cinema4D-1.3.0.zip",
          "browser_download_url": "https://x/c4d-1.3.0.zip"},
     ]},
    {"tag_name": "v1.2.0", "name": "v1.2.0", "body": "- two",
     "published_at": "2026-06-01T10:00:00Z",
     "assets": [{"name": "Overseer-Cinema4D-1.2.0.zip",
                 "browser_download_url": "https://x/c4d-1.2.0.zip"}]},
    {"tag_name": "v1.4.0", "name": "draft", "draft": True,
     "assets": [{"name": "Overseer-Cinema4D-1.4.0.zip",
                 "browser_download_url": "https://x/c4d-1.4.0.zip"}]},
    {"tag_name": "v1.1.0", "name": "v1.1.0", "body": "old",
     "published_at": "2026-05-01T10:00:00Z",
     "assets": [{"name": "Overseer-Cinema4D-1.1.0.zip",
                 "browser_download_url": "https://x/c4d-1.1.0.zip"}]},
]


def make_target(tmp_path, keep=(), version="1.1.0"):
    install = tmp_path / "Overseer"
    install.mkdir()
    (install / "overseer.pyp").write_text("old loader")
    (install / "logo.png").write_text("old logo")
    pkg = install / "overseer"
    pkg.mkdir()
    (pkg / "__init__.py").write_text('__version__ = "%s"' % version)
    (install / "config.json").write_text('{"schema": 3}')
    hist = install / "history"
    hist.mkdir()
    (hist / "scene.json").write_text("[]")
    (install / "__pycache__").mkdir()
    return updater.UpdateTarget(
        repo="x/y", current_version=version,
        install_dir=str(install), data_dir=str(install),
        asset_pattern="Overseer-Cinema4D-*.zip",
        payload_marker="overseer.pyp", disable_globs=("*.pyp",), keep=keep)


def make_payload_zip(tmp_path, version="1.3.0"):
    zip_path = tmp_path / ("Overseer-Cinema4D-%s.zip" % version)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("Overseer/overseer.pyp", "new loader")
        zf.writestr("Overseer/LICENSE", "mit")
        zf.writestr("Overseer/overseer/__init__.py",
                    '__version__ = "%s"' % version)
        zf.writestr("Overseer/web/index.html", "<html>")
    return zip_path


def test_parse_version_strips_prefix_and_suffix():
    # postcondition
    assert updater.parse_version("v1.2.3") == (1, 2, 3)
    assert updater.parse_version("1.10.0-rc2") == (1, 10, 0)
    assert updater.parse_version("") == (0,)


def test_is_newer_compares_numerically():
    # postcondition
    assert updater.is_newer("1.10.0", "1.9.9")
    assert updater.is_newer("2.0", "1.9.9")
    assert not updater.is_newer("1.2.0", "1.2.0")
    assert not updater.is_newer("1.1.9", "1.2")


def test_parse_releases_picks_matching_asset_and_skips_drafts():
    # do it
    releases = updater.parse_releases(RELEASES, "Overseer-Cinema4D-*.zip")

    # postcondition
    versions = [r.version for r in releases]
    assert versions == ["1.3.0", "1.2.0", "1.1.0"]
    assert releases[0].asset_url == "https://x/c4d-1.3.0.zip"
    assert releases[0].notes == "## New\n- three"
    assert releases[0].date == "2026-07-20"


def test_newer_releases_filters_and_sorts_newest_first():
    # setup
    releases = updater.parse_releases(RELEASES, "Overseer-Cinema4D-*.zip")

    # do it
    fresh = updater.newer_releases(releases, "1.1.0")

    # postcondition
    assert [r.version for r in fresh] == ["1.3.0", "1.2.0"]


def test_check_reports_latest_and_releases(tmp_path):
    # setup
    target = make_target(tmp_path)

    # do it
    out = updater.check(target, fetch=lambda repo: RELEASES)

    # postcondition
    assert out["ok"] and out["update_available"]
    assert out["latest"] == "1.3.0"
    assert [r["version"] for r in out["releases"]] == ["1.3.0", "1.2.0"]
    assert out["writable"] is True


def test_check_survives_a_failing_fetch(tmp_path):
    # setup
    def boom(repo):
        raise OSError("offline")

    # do it
    out = updater.check(make_target(tmp_path), fetch=boom)

    # postcondition
    assert out["ok"] is False and "offline" in out["error"]


def test_extract_payload_rejects_zip_slip(tmp_path):
    # setup
    bad = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("../evil.txt", "x")

    # do it
    try:
        updater.extract_payload(str(bad), str(tmp_path / "work"))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_install_swaps_preserves_user_data_and_writes_pending_state(tmp_path):
    # setup
    target = make_target(tmp_path)
    zip_src = make_payload_zip(tmp_path)
    release = updater.ReleaseInfo(
        version="1.3.0", name="v1.3.0", notes="", date="2026-07-20",
        asset_name=zip_src.name, asset_url="https://x/c4d-1.3.0.zip")

    def fake_download(url, dest, progress=None, timeout=60):
        with open(zip_src, "rb") as f:
            data = f.read()
        with open(dest, "wb") as out:
            out.write(data)
        if progress:
            progress(len(data), len(data))

    # do it
    out = updater.install(target, release, download=fake_download)

    # postcondition: shipped files replaced, user data carried over
    assert out["ok"] and out["restart_required"]
    install = tmp_path / "Overseer"
    assert (install / "overseer.pyp").read_text() == "new loader"
    assert (install / "LICENSE").read_text() == "mit"
    assert (install / "config.json").read_text() == '{"schema": 3}'
    assert (install / "history" / "scene.json").read_text() == "[]"
    assert (install / "logo.png").exists()  # no longer shipped -> carried over
    backup = tmp_path / "Overseer.backup-1.1.0"
    assert (backup / ("overseer.pyp" + updater.DISABLED_SUFFIX)).exists()
    assert not (backup / "overseer.pyp").exists()
    state = json.loads((install / updater.STATE_FILE).read_text())
    assert state["state"] == "pending" and state["boots"] == 0
    assert state["from"] == "1.1.0" and state["to"] == "1.3.0"


def test_swap_carries_unshipped_entries_but_not_pycache(tmp_path):
    # setup
    target = make_target(tmp_path)
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "overseer.pyp").write_text("new loader")

    # do it
    backup = updater.swap(target, str(payload))

    # postcondition
    install = tmp_path / "Overseer"
    assert (install / "config.json").exists()
    assert (install / "history" / "scene.json").exists()
    assert (install / "logo.png").exists()
    assert not (install / "__pycache__").exists()
    assert os.path.isdir(backup)


def test_swap_disables_the_blender_manifest_in_the_backup(tmp_path):
    # setup: a blender-addon-shaped install (extensions discovery keys on
    # blender_manifest.toml, so the backup's copy must be neutralized)
    install = tmp_path / "overseer"
    install.mkdir()
    (install / "__init__.py").write_text("old loader")
    (install / "blender_manifest.toml").write_text("id = overseer")
    target = updater.UpdateTarget(
        repo="x/y", current_version="1.1.0",
        install_dir=str(install), data_dir=str(install),
        asset_pattern="Overseer-Blender-*.zip", payload_marker="__init__.py",
        disable_globs=("blender_manifest.toml",))
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "__init__.py").write_text("new loader")
    (payload / "blender_manifest.toml").write_text("id = overseer")

    # do it
    backup = updater.swap(target, str(payload))

    # postcondition: manifest disabled, the loader itself stays (the dotted
    # backup folder name is already not importable)
    assert not os.path.exists(os.path.join(backup, "blender_manifest.toml"))
    assert os.path.exists(os.path.join(
        backup, "blender_manifest.toml" + updater.DISABLED_SUFFIX))
    assert os.path.exists(os.path.join(backup, "__init__.py"))


def test_note_boot_rolls_back_after_boot_limit(tmp_path):
    # setup
    target = make_target(tmp_path)
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "overseer.pyp").write_text("broken loader")
    backup = updater.swap(target, str(payload))
    updater.write_state(target.data_dir, {
        "state": "pending", "from": "1.1.0", "to": "1.3.0",
        "backup": backup, "boots": 0})

    # do it
    results = [updater.note_boot(target) for _ in range(updater.BOOT_LIMIT)]

    # postcondition: restored on the last boot, failed copy disabled
    assert results[:-1] == [None] * (updater.BOOT_LIMIT - 1)
    assert results[-1]["state"] == "rolled_back"
    install = tmp_path / "Overseer"
    assert (install / "overseer.pyp").read_text() == "old loader"
    failed = results[-1]["failed"]
    assert (os.path.exists(os.path.join(
        failed, "overseer.pyp" + updater.DISABLED_SUFFIX)))
    assert updater.read_state(target.data_dir)["state"] == "rolled_back"


def test_failed_start_rolls_back_a_pending_update(tmp_path):
    # setup
    target = make_target(tmp_path)
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "overseer.pyp").write_text("broken loader")
    backup = updater.swap(target, str(payload))
    updater.write_state(target.data_dir, {
        "state": "pending", "from": "1.1.0", "to": "1.3.0",
        "backup": backup, "boots": 1})

    # do it
    state = updater.failed_start(target)

    # postcondition
    assert state["state"] == "rolled_back"
    assert (tmp_path / "Overseer" / "overseer.pyp").read_text() == "old loader"


def test_confirm_ok_needs_a_restart_and_prunes_old_siblings(tmp_path):
    # setup
    target = make_target(tmp_path)
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "overseer.pyp").write_text("new loader")
    backup = updater.swap(target, str(payload))
    stale = tmp_path / "Overseer.backup-1.0.0"
    stale.mkdir()
    updater.write_state(target.data_dir, {
        "state": "pending", "from": "1.1.0", "to": "1.3.0",
        "backup": backup, "boots": 0})

    # do it: first request in the install session must NOT confirm
    updater.confirm_ok(target)
    assert updater.read_state(target.data_dir)["state"] == "pending"
    updater.note_boot(target)
    updater.confirm_ok(target)

    # postcondition: confirmed after one boot, stale backup pruned, own kept
    assert updater.read_state(target.data_dir)["state"] == "ok"
    assert not stale.exists()
    assert os.path.isdir(backup)


def test_acknowledge_clears_terminal_states_only(tmp_path):
    # setup
    data_dir = str(tmp_path)
    updater.write_state(data_dir, {"state": "pending"})

    # do it
    updater.acknowledge(data_dir)
    assert updater.read_state(data_dir) == {"state": "pending"}
    updater.write_state(data_dir, {"state": "rolled_back"})
    updater.acknowledge(data_dir)

    # postcondition
    assert updater.read_state(data_dir) == {}
