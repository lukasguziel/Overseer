from __future__ import annotations

import fnmatch
import json
import os
import re
import shutil
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass

GITHUB_RELEASES_URL = "https://api.github.com/repos/%s/releases"
STATE_FILE = "update_state.json"
DISABLED_SUFFIX = ".off"
BACKUP_TAG = ".backup-"
FAILED_TAG = ".failed-"
BOOT_LIMIT = 3
CHECK_TTL = 6 * 3600
USER_AGENT = "Overseer-Updater"

_SWAP_EXCLUDE = {"__pycache__"}


@dataclass
class ReleaseInfo:
    version: str
    name: str
    notes: str
    date: str
    asset_name: str
    asset_url: str

    def to_dict(self) -> dict:
        return {"version": self.version, "name": self.name,
                "notes": self.notes, "date": self.date,
                "asset": self.asset_name, "asset_url": self.asset_url}


@dataclass
class UpdateTarget:
    repo: str
    current_version: str
    install_dir: str
    data_dir: str
    asset_pattern: str
    payload_marker: str = ""
    disable_globs: tuple = ()
    keep: tuple = ()


def parse_version(text) -> tuple:
    base = str(text or "").strip().lstrip("vV").split("-")[0]
    nums = re.findall(r"\d+", base)
    return tuple(int(n) for n in nums) if nums else (0,)


def is_newer(candidate, current) -> bool:
    a, b = parse_version(candidate), parse_version(current)
    size = max(len(a), len(b))
    return a + (0,) * (size - len(a)) > b + (0,) * (size - len(b))


def parse_releases(data, asset_pattern: str) -> list:
    releases = []
    for entry in data or []:
        if not isinstance(entry, dict) or entry.get("draft") \
                or entry.get("prerelease"):
            continue
        tag = str(entry.get("tag_name") or "")
        asset_name = asset_url = ""
        for asset in entry.get("assets") or []:
            name = str(asset.get("name") or "")
            if fnmatch.fnmatch(name, asset_pattern):
                asset_name = name
                asset_url = str(asset.get("browser_download_url") or "")
                break
        if not asset_url:
            continue
        releases.append(ReleaseInfo(
            version=tag.lstrip("vV") or str(entry.get("name") or ""),
            name=str(entry.get("name") or tag),
            notes=str(entry.get("body") or ""),
            date=str(entry.get("published_at") or "")[:10],
            asset_name=asset_name, asset_url=asset_url))
    return releases


def newer_releases(releases, current: str) -> list:
    fresh = [r for r in releases if is_newer(r.version, current)]
    fresh.sort(key=lambda r: parse_version(r.version), reverse=True)
    return fresh


def fetch_release_list(repo: str, timeout: int = 10) -> list:
    req = urllib.request.Request(
        GITHUB_RELEASES_URL % repo,
        headers={"User-Agent": USER_AGENT,
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data if isinstance(data, list) else []


def check(target: UpdateTarget, fetch=fetch_release_list) -> dict:
    try:
        raw = fetch(target.repo)
    except Exception as ex:  # noqa: BLE001
        return {"ok": False, "error": "update check failed: %s" % ex}
    fresh = newer_releases(parse_releases(raw, target.asset_pattern),
                           target.current_version)
    return {"ok": True,
            "current": target.current_version,
            "latest": fresh[0].version if fresh else target.current_version,
            "update_available": bool(fresh),
            "writable": swap_supported(target.install_dir),
            "releases": [r.to_dict() for r in fresh]}


def swap_supported(install_dir: str) -> bool:
    parent = os.path.dirname(os.path.abspath(install_dir))
    return os.path.isdir(install_dir) and _writable(install_dir) \
        and _writable(parent)


def _writable(path: str) -> bool:
    probe = os.path.join(path, ".ovr_write_probe")
    try:
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        return True
    except OSError:
        return False


def read_state(data_dir: str) -> dict:
    try:
        with open(os.path.join(data_dir, STATE_FILE), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(data_dir: str, state: dict) -> None:
    try:
        with open(os.path.join(data_dir, STATE_FILE), "w",
                  encoding="utf-8") as f:
            json.dump(state, f, indent=1)
    except OSError:
        pass


def clear_state(data_dir: str) -> None:
    try:
        os.remove(os.path.join(data_dir, STATE_FILE))
    except OSError:
        pass


def acknowledge(data_dir: str) -> None:
    if read_state(data_dir).get("state") in ("ok", "rolled_back", "failed"):
        clear_state(data_dir)


def download_asset(url: str, dest: str, progress=None,
                   timeout: int = 60) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        with open(dest, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)


def extract_payload(zip_path: str, work_dir: str, marker: str = "") -> str:
    out = os.path.join(work_dir, "payload")
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename.replace("\\", "/")
            if name.startswith("/") or ".." in name.split("/"):
                raise ValueError("unsafe zip entry: %s" % info.filename)
        zf.extractall(out)
    entries = os.listdir(out)
    root = out
    if len(entries) == 1 and os.path.isdir(os.path.join(out, entries[0])):
        root = os.path.join(out, entries[0])
    if marker and not os.path.exists(os.path.join(root, marker)):
        raise ValueError("downloaded zip has no %s at its root" % marker)
    return root


def disable_loaders(root: str, globs) -> None:
    for base, _dirs, files in os.walk(root):
        for name in files:
            if any(fnmatch.fnmatch(name, g) for g in globs or ()):
                os.rename(os.path.join(base, name),
                          os.path.join(base, name + DISABLED_SUFFIX))


def enable_loaders(root: str) -> None:
    for base, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(DISABLED_SUFFIX):
                os.rename(os.path.join(base, name),
                          os.path.join(base, name[:-len(DISABLED_SUFFIX)]))


def _unique_dir(base: str) -> str:
    path, n = base, 2
    while os.path.exists(path):
        path = "%s-%d" % (base, n)
        n += 1
    return path


def _copy_entry(src: str, dst: str) -> None:
    if os.path.isdir(src):
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def swap(target: UpdateTarget, payload_root: str) -> str:
    backup = _unique_dir(
        target.install_dir + BACKUP_TAG + target.current_version)
    os.rename(target.install_dir, backup)
    try:
        shutil.move(payload_root, target.install_dir)
    except Exception:
        os.rename(backup, target.install_dir)
        raise
    shipped = set(os.listdir(target.install_dir))
    for entry in os.listdir(backup):
        if entry in _SWAP_EXCLUDE or entry == STATE_FILE:
            continue
        kept = any(fnmatch.fnmatch(entry, k) for k in target.keep)
        if entry in shipped and not kept:
            continue
        _copy_entry(os.path.join(backup, entry),
                    os.path.join(target.install_dir, entry))
    disable_loaders(backup, target.disable_globs)
    return backup


def install(target: UpdateTarget, release: ReleaseInfo, progress=None,
            download=download_asset) -> dict:
    if not swap_supported(target.install_dir):
        return {"ok": False,
                "error": "The install folder is not writable (%s) - "
                         "update it manually." % target.install_dir}
    work = tempfile.mkdtemp(prefix="overseer-update-")
    try:
        zip_path = os.path.join(work, release.asset_name or "update.zip")
        if progress:
            progress("download", 0, 0)
        download(release.asset_url, zip_path,
                 progress=(lambda done, total: progress("download", done,
                                                        total))
                 if progress else None)
        payload = extract_payload(zip_path, work, target.payload_marker)
        if progress:
            progress("install", 0, 0)
        backup = swap(target, payload)
    except Exception as ex:  # noqa: BLE001
        return {"ok": False, "error": "update failed: %s" % ex}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    write_state(target.data_dir, {
        "state": "pending", "from": target.current_version,
        "to": release.version, "backup": backup, "boots": 0,
        "ts": time.time()})
    return {"ok": True, "installed": release.version,
            "from": target.current_version, "backup": backup,
            "restart_required": True}


def note_boot(target: UpdateTarget):
    state = read_state(target.data_dir)
    if state.get("state") != "pending":
        return None
    state["boots"] = int(state.get("boots") or 0) + 1
    if state["boots"] >= BOOT_LIMIT:
        return rollback(target, "the update was never confirmed after "
                                "%d starts" % state["boots"])
    write_state(target.data_dir, state)
    return None


def confirm_ok(target_or_data_dir) -> None:
    data_dir = getattr(target_or_data_dir, "data_dir", target_or_data_dir)
    state = read_state(data_dir)
    if state.get("state") != "pending" or int(state.get("boots") or 0) < 1:
        return
    state["state"] = "ok"
    write_state(data_dir, state)
    install_dir = getattr(target_or_data_dir, "install_dir", "")
    if install_dir:
        _prune_siblings(install_dir, keep=state.get("backup") or "")


def failed_start(target: UpdateTarget):
    if read_state(target.data_dir).get("state") != "pending":
        return None
    return rollback(target, "the updated version failed to start")


def rollback(target: UpdateTarget, reason: str) -> dict:
    state = read_state(target.data_dir)
    backup = str(state.get("backup") or "")
    if not os.path.isdir(backup):
        state.update({"state": "failed",
                      "reason": "%s; no backup found to restore" % reason})
        write_state(target.data_dir, state)
        return state
    failed = _unique_dir(
        target.install_dir + FAILED_TAG + str(state.get("to") or "unknown"))
    try:
        os.rename(target.install_dir, failed)
        try:
            os.rename(backup, target.install_dir)
        except OSError:
            os.rename(failed, target.install_dir)
            raise
        enable_loaders(target.install_dir)
        disable_loaders(failed, target.disable_globs)
    except OSError as ex:
        state.update({"state": "failed",
                      "reason": "%s; rollback failed: %s" % (reason, ex)})
        write_state(target.data_dir, state)
        return state
    state.update({"state": "rolled_back", "reason": reason, "failed": failed})
    write_state(target.data_dir, state)
    return state


def _prune_siblings(install_dir: str, keep: str = "") -> None:
    parent = os.path.dirname(os.path.abspath(install_dir))
    base = os.path.basename(os.path.abspath(install_dir))
    keep_abs = os.path.abspath(keep) if keep else ""
    try:
        names = os.listdir(parent)
    except OSError:
        return
    for name in names:
        if not (name.startswith(base + BACKUP_TAG)
                or name.startswith(base + FAILED_TAG)):
            continue
        path = os.path.join(parent, name)
        if keep_abs and os.path.abspath(path) == keep_abs:
            continue
        shutil.rmtree(path, ignore_errors=True)
