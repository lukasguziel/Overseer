"""Host-neutral web-API IO helpers shared by the C4D and Blender backends.

Pure Python: no ``c4d``, no ``bpy``. Everything here is parameterised on plain
strings/dicts (data dir, document path/name, report dicts) instead of a live
host document, so both ``cinema/webapi.py`` and ``blender/webapi.py`` can reuse
it and it is unit-testable without either host.

The C4D backend historically kept private copies of this logic inside
``cinema/webapi.py``; that copy is left in place (do not destabilise the
shipped plugin). New code — the Blender port — routes through here.
"""
from __future__ import annotations

import json
import os

# ---------------------------------------------------------------------------
# limits (mirror cinema/webapi.py)
# ---------------------------------------------------------------------------
HISTORY_MAX = 100
CHANGES_MAX = 200
GCACHE_MAX = 20000

CSV_FIELDS = ("path", "name", "type", "category", "depth", "casing",
              "language", "children")


# ---------------------------------------------------------------------------
# writable-dir probing / data dir
# ---------------------------------------------------------------------------
def writable(directory: str) -> bool:
    probe = os.path.join(directory, ".write_probe")
    try:
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        return True
    except OSError:
        return False


def resolve_data_dir(plugin_dir: str, prefs_base: str | None,
                     app_name: str = "overseer",
                     legacy_name: str = "scene_organizer") -> str:
    """Where to write config/history/caches.

    Prefer the plugin dir when writable (dev checkout); otherwise a per-user
    app dir under ``prefs_base`` (host prefs dir), falling back to
    ``%APPDATA%``/``~``. Migrates a legacy folder name if present.
    """
    if writable(plugin_dir):
        return plugin_dir
    base = prefs_base or os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, app_name)
    legacy = os.path.join(base, legacy_name)
    if not os.path.isdir(path) and os.path.isdir(legacy):
        try:
            os.rename(legacy, path)
        except OSError:
            path = legacy
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


# ---------------------------------------------------------------------------
# config.json
# ---------------------------------------------------------------------------
def read_config_data(config_path: str) -> dict:
    if os.path.isfile(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def write_config_data(config_path: str, data: dict) -> None:
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def seed_config(plugin_dir: str, config_path: str) -> None:
    """Copy a bundled seed config next to the plugin into the data dir once."""
    if os.path.dirname(config_path) == plugin_dir:
        return
    seed = os.path.join(plugin_dir, "config.json")
    if os.path.isfile(seed) and not os.path.isfile(config_path):
        import shutil
        try:
            shutil.copy2(seed, config_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# report export (json + csv)
# ---------------------------------------------------------------------------
def write_export(report_dict: dict, export_path: str,
                 target_dir: str | None = None) -> str | None:
    primary = None
    if target_dir and os.path.isdir(target_dir):
        try:
            p = os.path.join(target_dir, "scene_report.json")
            with open(p, "w") as f:
                json.dump(report_dict, f, ensure_ascii=True, indent=1)
            primary = p
        except Exception:
            primary = None
    try:
        if os.path.isdir(os.path.dirname(export_path)):
            with open(export_path, "w") as f:
                json.dump(report_dict, f, ensure_ascii=True, indent=1)
            if primary is None:
                primary = export_path
    except Exception:
        pass
    return primary


def write_csv(report_dict: dict, csv_path: str,
              target_dir: str | None = None) -> tuple[str, int] | None:
    import csv
    path = (os.path.join(target_dir, "scene_structure.csv")
            if target_dir and os.path.isdir(target_dir) else csv_path)
    try:
        if not os.path.isdir(os.path.dirname(path)):
            return None
        nodes = report_dict.get("nodes", [])
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=";",
                               extrasaction="ignore")
            w.writeheader()
            for n in nodes:
                w.writerow(n)
        return path, len(nodes)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# per-project analysis history
# ---------------------------------------------------------------------------
def history_path(history_dir: str, slug: str) -> str:
    try:
        os.makedirs(history_dir, exist_ok=True)
    except OSError:
        pass
    return os.path.join(history_dir, (slug or "project") + ".json")


def read_history(path: str, legacy_path: str = "",
                 doc_name: str = "") -> list:
    try:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    return _legacy_history(legacy_path, doc_name)


def _legacy_history(legacy_path: str, doc_name: str) -> list:
    try:
        if not legacy_path or not os.path.isfile(legacy_path):
            return []
        with open(legacy_path, encoding="utf-8") as f:
            hist = json.load(f) or []
        return [e for e in hist if e.get("file") == doc_name][-HISTORY_MAX:]
    except Exception:
        return []


def record_history(path: str, entry: dict, legacy_path: str = "",
                   doc_name: str = "") -> None:
    try:
        hist = read_history(path, legacy_path, doc_name)
        last = hist[-1] if hist else None
        if (last and last.get("file") == entry.get("file")
                and abs(entry["ts"] - last.get("ts", 0)) < 60):
            hist[-1] = entry
        else:
            hist.append(entry)
        hist = hist[-HISTORY_MAX:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# google translate cache + online plan (network is best-effort)
# ---------------------------------------------------------------------------
def load_gcache(path: str) -> dict:
    try:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def save_gcache(path: str, cache: dict) -> None:
    try:
        if len(cache) > GCACHE_MAX:
            cache = dict(list(cache.items())[len(cache) // 2:])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass


def _gcache_text(entry) -> str:
    if isinstance(entry, dict):
        return str(entry.get("t") or "")
    return str(entry or "")


def _gcache_src(entry) -> str:
    if isinstance(entry, dict):
        return str(entry.get("src") or "unknown")
    return "unknown"


def google_plan(tree, scope, target: str, gcache_path: str,
                progress=None):
    """Online (Google) translation plan. Returns (proposals, err, detected).

    Mirrors ``cinema/webapi.py::_google_plan`` exactly; pure except for the
    urllib fetch and the on-disk cache at ``gcache_path``.
    """
    import json as _json
    import urllib.parse
    import urllib.request

    from .naming import translate as translatemod

    nodes = [n for n in tree.walk()
             if (scope is None or n.guid in scope) and n.name.strip()]
    if not nodes:
        return [], None, {"total": 0, "counts": {}, "dominant": "unknown"}

    cache = load_gcache(gcache_path)

    def key(word: str) -> str:
        return target + "\x00" + word

    todo: list = []
    seen: set = set()
    for n in nodes:
        for word in translatemod.translatable_words(n.name):
            k = key(word)
            entry = cache.get(k)
            if (entry is None or isinstance(entry, str)) and k not in seen:
                seen.add(k)
                todo.append(word)

    err = None
    batch = 40
    fetched = 0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        if progress:
            progress(fetched, len(todo))
        q = "\n".join(chunk)
        url = ("https://translate.googleapis.com/translate_a/single"
               "?client=gtx&sl=auto&tl=%s&dt=t&q=%s"
               % (urllib.parse.quote(target), urllib.parse.quote(q)))
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = _json.loads(r.read().decode("utf-8"))
            text = "".join(s[0] for s in (data[0] or []) if s and s[0])
            lines = text.split("\n")
            try:
                src = str(data[2] or "unknown")
            except Exception:
                src = "unknown"
        except Exception as ex:  # noqa: BLE001 - network is best-effort
            err = str(ex)
            break
        if len(lines) != len(chunk):
            err = "batch mismatch (%d names -> %d lines)" % (
                len(chunk), len(lines))
            continue
        for word, new in zip(chunk, lines):  # noqa: B905
            cache[key(word)] = {"t": new.strip(), "src": src}
        fetched += len(chunk)
    if todo:
        save_gcache(gcache_path, cache)
    if progress:
        progress(len(todo), len(todo))

    proposals = []
    counts: dict = {}
    for node in nodes:
        words = translatemod.translatable_words(node.name)
        mapping = {}
        langs: list = []
        for word in words:
            entry = cache.get(key(word))
            if entry is None:
                continue
            mapping[word] = _gcache_text(entry)
            src = _gcache_src(entry)
            if src != "unknown":
                langs.append(src)
        new, changed = translatemod.rebuild_with(node.name, mapping)
        src = max(set(langs), key=langs.count) if langs else "unknown"
        if changed:
            bucket = src
        elif mapping:
            bucket = target
        else:
            bucket = "unknown"
        counts[bucket] = counts.get(bucket, 0) + 1
        if changed and new != node.name:
            proposals.append(translatemod.TranslateProposal(
                node=node, new=new, words=changed,
                lang=src if src != "unknown" else "auto"))
    dominant = max(counts, key=counts.get) if counts else "unknown"
    detected = {"total": len(nodes), "counts": counts, "dominant": dominant}
    return proposals, err, detected


# ---------------------------------------------------------------------------
# net info
# ---------------------------------------------------------------------------
def lan_ip():
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        return None
