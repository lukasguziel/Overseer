from __future__ import annotations

import json
import os

import c4d

from .. import config as cfgmod
from ..core import journal as journalmod
from ..core import keeps as keepsmod
from ..core import layers as layersmod
from ..core import ops, pipeline
from ..core.analyzer import SceneAnalyzer
from ..naming import detect as detectmod
from ..naming import translate as translatemod
from ..naming import translations
from ..naming.casing import Casing
from ..naming.convention import NamingConvention
from ..structure import graph as graphmod
from . import adapter as adaptermod
from .adapter import SceneAdapter

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _writable(directory: str) -> bool:
    probe = os.path.join(directory, ".write_probe")
    try:
        with open(probe, "w") as f:
            f.write("x")
        os.remove(probe)
        return True
    except OSError:
        return False


def _user_data_dir() -> str:
    if _writable(PLUGIN_DIR):
        return PLUGIN_DIR
    try:
        base = c4d.storage.GeGetC4DPath(c4d.C4D_PATH_PREFS)
    except Exception:
        base = None
    if not base:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "scene_organizer")
    os.makedirs(path, exist_ok=True)
    return path


DATA_DIR = _user_data_dir()
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
SHIPPED_PRESETS_DIR = os.path.join(PLUGIN_DIR, "presets")
PRESETS_DIR = os.path.join(DATA_DIR, "presets")
PLANS_DIR = os.path.join(PLUGIN_DIR, "plans")

if DATA_DIR != PLUGIN_DIR:
    _seed = os.path.join(PLUGIN_DIR, "config.json")
    if os.path.isfile(_seed) and not os.path.isfile(CONFIG_PATH):
        import shutil
        try:
            shutil.copy2(_seed, CONFIG_PATH)
        except OSError:
            pass

def _export_dir() -> str:
    env = os.environ.get("SCENEORG_EXPORT_DIR")
    if env and os.path.isdir(env):
        return env
    try:
        stamp = os.path.join(PLUGIN_DIR, "dev_repo.txt")
        if os.path.isfile(stamp):
            with open(stamp, encoding="utf-8-sig") as f:
                repo = f.read().strip()
            if repo and os.path.isdir(repo):
                return repo
    except OSError:
        pass
    return DATA_DIR


EXPORT_PATH = os.path.join(_export_dir(), "scene_report.json")
EXPORT_CSV_PATH = os.path.join(_export_dir(), "scene_structure.csv")
# Per-project analysis logs live in history/<project-slug>.json; the flat
# analysis_history.json is the pre-split log, still read as a seed.
HISTORY_DIR = os.path.join(DATA_DIR, "history")
HISTORY_PATH = os.path.join(DATA_DIR, "analysis_history.json")
_HISTORY_MAX = 100

CHANGES_PATH = os.path.join(DATA_DIR, "change_history.json")
_CHANGES_MAX = 200

_CSV_FIELDS = ("path", "name", "type", "category", "depth", "casing",
               "language", "children")


def _load_journal(doc) -> list:
    return adaptermod.load_journal(doc, CHANGES_PATH)


def _save_journal(doc, entries: list) -> None:
    adaptermod.save_journal(doc, entries[-_CHANGES_MAX:], CHANGES_PATH)


def _record_change(kind: str, summary: str, items: list,
                   revertible: bool = True, doc=None,
                   doc_name: str = "") -> dict | None:
    if not items and not summary:
        return None
    import time
    now = time.time()
    for it in (items or []):
        it.setdefault("reverted", False)
    entry = {
        "id": "%d" % int(now * 1000),
        "ts": now,
        "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "kind": kind,
        "summary": summary,
        "doc": doc_name or (doc.GetDocumentName() if doc is not None else ""),
        "items": items or [],
        "revertible": bool(revertible and items),
        "reverted": False,
    }
    if doc is not None:
        entries = _load_journal(doc)
        entries.append(entry)
        _save_journal(doc, entries)
    return entry


def _write_export(report_dict, target_dir: str | None = None) -> str | None:
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
        if os.path.isdir(os.path.dirname(EXPORT_PATH)):
            with open(EXPORT_PATH, "w") as f:
                json.dump(report_dict, f, ensure_ascii=True, indent=1)
            if primary is None:
                primary = EXPORT_PATH
    except Exception:
        pass
    return primary


def _write_csv(report_dict, target_dir: str | None = None) -> tuple[str, int] | None:
    import csv
    if target_dir and os.path.isdir(target_dir):
        path = os.path.join(target_dir, "scene_structure.csv")
    else:
        path = EXPORT_CSV_PATH
    try:
        if not os.path.isdir(os.path.dirname(path)):
            return None
        nodes = report_dict.get("nodes", [])
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=_CSV_FIELDS, delimiter=";",
                               extrasaction="ignore")
            w.writeheader()
            for n in nodes:
                w.writerow(n)
        return path, len(nodes)
    except Exception:
        return None


def _history_path(doc) -> str:
    """Per-project log file — same project slug the UI settings use, so one
    project's runs never crowd out another's (the log is capped per project)."""
    from ..core import ui_settings_logic as uilogic
    slug = uilogic.project_slug(doc.GetDocumentPath() or "",
                                doc.GetDocumentName() or "") or "project"
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
    except OSError:
        pass
    return os.path.join(HISTORY_DIR, slug + ".json")


def _read_history(doc) -> list:
    path = _history_path(doc)
    try:
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    # No per-project log yet: seed it from the pre-split global log (kept as
    # an archive) with the runs that belong to this document.
    return _legacy_history(doc.GetDocumentName() or "")


def _legacy_history(doc_name: str) -> list:
    try:
        if not os.path.isfile(HISTORY_PATH):
            return []
        with open(HISTORY_PATH, encoding="utf-8") as f:
            hist = json.load(f) or []
        return [e for e in hist if e.get("file") == doc_name][-_HISTORY_MAX:]
    except Exception:
        return []


def _record_history(doc, entry: dict) -> None:
    try:
        hist = _read_history(doc)
        last = hist[-1] if hist else None
        if (last and last.get("file") == entry.get("file")
                and abs(entry["ts"] - last.get("ts", 0)) < 60):
            hist[-1] = entry
        else:
            hist.append(entry)
        hist = hist[-_HISTORY_MAX:]
        with open(_history_path(doc), "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _merge_layers(report_dict: dict, layer_meta: list,
                  all_object_counts: dict | None = None) -> dict:
    return layersmod.build_layer_report(
        layer_meta,
        object_counts=dict(report_dict.get("layers_by_name") or {}),
        poly_counts=dict(report_dict.get("polys_by_layer") or {}),
        no_layer=report_dict.get("no_layer_count", 0),
        all_object_counts=all_object_counts)


def _read_config_data() -> dict:
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _lan_ip():
    """The machine's LAN address — a connectionless UDP 'connect' just picks
    the outbound interface, nothing is sent."""
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


def _netinfo(payload: dict) -> dict:
    """LAN state for the open-on-phone QR flow. POST {"listen_lan": bool}
    persists the opt-in; the bind itself only changes on a C4D restart."""
    from .. import bridge
    # getattr: bridge is the never-hot-reloaded singleton — right after a
    # deploy the RUNNING bridge may predate lan_enabled() until a C4D restart.
    lan = bool(getattr(bridge, "lan_enabled", lambda: False)())
    changed = False
    if "listen_lan" in payload:
        data = _read_config_data()
        data["listen_lan"] = bool(payload["listen_lan"])
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        changed = data["listen_lan"] != lan
    return {"ok": True,
            "lan": lan,
            "wanted": bool(_read_config_data().get("listen_lan", False)),
            "restart_needed": changed,
            "ip": _lan_ip(),
            "port": getattr(bridge, "DEFAULT_PORT", 8787)}


def _preset_settings(data: dict) -> dict:
    if "settings" in data:
        return data.get("settings") or {}
    return {k: v for k, v in data.items() if k != "meta"}


def _preset_dirs() -> list:
    dirs = [PRESETS_DIR]
    if SHIPPED_PRESETS_DIR != PRESETS_DIR:
        dirs.append(SHIPPED_PRESETS_DIR)
    return dirs


def _list_presets() -> list:
    out = []
    seen: set = set()
    for directory in _preset_dirs():
        try:
            if not os.path.isdir(directory):
                continue
            for fn in sorted(os.listdir(directory)):
                if not fn.endswith(".json") or fn in seen:
                    continue
                seen.add(fn)
                try:
                    with open(os.path.join(directory, fn), encoding="utf-8") as f:
                        data = json.load(f)
                    meta = data.get("meta", {})
                    settings = cfgmod.migrate_config(_preset_settings(data))
                    groups = [g.get("name", "?")
                              for g in (settings.get("structure") or [])]
                    out.append({
                        "id": meta.get("id") or fn[:-5],
                        "name": meta.get("name") or fn[:-5],
                        "description": meta.get("description", ""),
                        "created_at": meta.get("created_at", ""),
                        "rules": len(settings.get("rules") or []),
                        "groups": groups,
                    })
                except Exception:
                    continue
        except Exception:
            continue
    return out


def _slugify(name: str) -> str:
    out = []
    for ch in name.strip().lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-") or "preset"


def _save_preset(name: str, description: str, overwrite: bool = False) -> dict:
    if not name.strip():
        return {"error": "preset needs a name"}
    import time
    slug = _slugify(name)
    if not os.path.isdir(PRESETS_DIR):
        os.makedirs(PRESETS_DIR)
    path = os.path.join(PRESETS_DIR, slug + ".json")
    if os.path.isfile(path) and not overwrite:
        return {"error": "preset '%s' exists (send overwrite:true to replace)"
                % slug, "exists": True, "id": slug}
    settings = cfgmod.migrate_config(_read_config_data())
    settings.pop("preset", None)
    preset = {
        "schema": 2,
        "meta": {
            "id": slug,
            "name": name.strip(),
            "description": description.strip(),
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "settings": settings,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(preset, f, indent=2, ensure_ascii=False)
    return {"ok": True, "id": slug, "path": path}


def _delete_preset(preset_id: str) -> dict:
    fn = os.path.basename(preset_id)
    if not fn.endswith(".json"):
        fn += ".json"
    for directory in _preset_dirs():
        path = os.path.join(directory, fn)
        if not os.path.isfile(path):
            continue
        try:
            os.remove(path)
        except OSError:
            return {"error": "preset '%s' is shipped with the plugin and "
                    "cannot be deleted" % preset_id}
        return {"ok": True, "deleted": preset_id}
    return {"error": "preset not found: %s" % preset_id}


def _load_preset(preset_id: str) -> dict | None:
    for directory in _preset_dirs():
        for cand in (preset_id, preset_id + ".json"):
            path = os.path.join(directory, os.path.basename(cand))
            if os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    return None
    return None


def _list_plans() -> list:
    out = []
    try:
        if not os.path.isdir(PLANS_DIR):
            return out
        for fn in sorted(os.listdir(PLANS_DIR)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(PLANS_DIR, fn), encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("meta", {})
                out.append({
                    "id": fn[:-5],
                    "name": meta.get("name") or fn[:-5],
                    "description": meta.get("description", ""),
                    "scene": meta.get("scene", ""),
                    "operations": len(data.get("operations", [])),
                })
            except Exception:
                continue
    except Exception:
        pass
    return out


def _load_plan(plan_id: str) -> dict | None:
    for cand in (plan_id, plan_id + ".json"):
        path = os.path.join(PLANS_DIR, os.path.basename(cand))
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
    return None


def _apply_preset(preset_id: str) -> dict:
    preset = _load_preset(preset_id)
    if preset is None:
        return {"error": "preset not found: %s" % preset_id}
    cfg = cfgmod.migrate_config(_preset_settings(preset))
    if not cfg.get("graph"):
        cfg["graph"] = graphmod.graph_from_structure(cfg.get("structure") or [])
    cfg["preset"] = preset.get("meta", {}).get("id") or preset_id
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return {"ok": True, "applied": cfg.get("preset"),
            "rules": len(cfg.get("rules") or []),
            "groups": len(cfg.get("structure") or [])}


def _load_cfg():
    data = _read_config_data()
    cfg = cfgmod.load_config(data)
    if cfg.extra_translations:
        translations.add_translations(cfg.extra_translations)
    return cfg, data


def _convention(settings: dict, cfg) -> NamingConvention:
    casing = settings.get("casing") or cfg.convention.style.value
    pad = int(settings.get("number_pad", cfg.convention.number_pad))
    apply_numbering = bool(settings.get("apply_numbering", True))
    apply_casing = bool(settings.get("apply_casing", True))
    keep_separators = bool(settings.get("keep_separators", False))
    keep_specials = bool(settings.get("keep_specials", True))
    return NamingConvention(style=Casing(casing), language=None, number_pad=pad,
                            apply_numbering=apply_numbering, apply_casing=apply_casing,
                            keep_separators=keep_separators,
                            keep_specials=keep_specials)


def _scope(settings: dict, adapter: SceneAdapter):
    if settings.get("selection"):
        return adapter.selected_guids()
    return None


def _rule_dict(r) -> dict:
    return {
        "name": r.name,
        "parent": r.parent,
        "path": r.path,
        "categories": sorted(r.match_categories),
        "keywords": sorted(r.match_keywords),
        "aliases": sorted(r.aliases),
        "priority": r.priority,
    }


GOOGLE_CACHE_PATH = os.path.join(DATA_DIR, "google_cache.json")
_GCACHE_MAX = 20000


def _load_gcache() -> dict:
    try:
        if os.path.isfile(GOOGLE_CACHE_PATH):
            with open(GOOGLE_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}


def _save_gcache(cache: dict) -> None:
    try:
        if len(cache) > _GCACHE_MAX:
            cache = dict(list(cache.items())[len(cache) // 2:])
        with open(GOOGLE_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass


def _gcache_text(entry):
    if isinstance(entry, dict):
        return str(entry.get("t") or "")
    return str(entry or "")


def _gcache_src(entry) -> str:
    if isinstance(entry, dict):
        return str(entry.get("src") or "unknown")
    return "unknown"


def _google_plan(tree, scope, target: str, progress=None):
    import json as _json
    import urllib.parse
    import urllib.request

    nodes = [n for n in tree.walk()
             if (scope is None or n.guid in scope) and n.name.strip()]
    if not nodes:
        return [], None, {"total": 0, "counts": {}, "dominant": "unknown"}

    cache = _load_gcache()

    def key(word: str) -> str:
        return target + "\x00" + word

    # Translate WORDS, not raw names. "body_rear_wing_part_usm.1" means nothing
    # to a translator — "body", "rear", "wing", "part" are trivial. Words also
    # repeat across a scene, so the cache hit rate is far higher than per name.
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
        _save_gcache(cache)
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
        # The name's source language is what most of its words came from.
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


def _progress(phase, current=0, total=0, detail=""):
    from .. import bridge
    bridge.set_progress(phase, current, total, detail)
    try:
        c4d.StatusSetText("Scene Organizer: %s" % phase)
        if total:
            c4d.StatusSetBar(int(current * 100 / max(1, total)))
        else:
            c4d.StatusSetSpin()
    except Exception:
        pass


def _clear_progress():
    from .. import bridge
    bridge.clear_progress()
    try:
        c4d.StatusClear()
    except Exception:
        pass


def _cache_store() -> dict:
    import sceneorg
    if not hasattr(sceneorg, "_scene_cache"):
        sceneorg._scene_cache = {}
    return sceneorg._scene_cache


def _refresh_selection(adapter, tree) -> None:
    adapter._selected_direct.clear()
    adapter._selected_subtree.clear()

    def visit(node, sel_ancestor):
        op = adapter._by_guid.get(node.guid)
        is_sel = False
        if op is not None:
            try:
                is_sel = bool(op.GetBit(c4d.BIT_ACTIVE))
            except Exception:
                is_sel = False
        if is_sel:
            adapter._selected_direct.add(node.guid)
        in_scope = sel_ancestor or is_sel
        if in_scope:
            adapter._selected_subtree.add(node.guid)
        for child in node.children:
            visit(child, in_scope)

    for root in tree.roots:
        visit(root, False)


def _get_scene(doc, label: str):
    cache = _cache_store()
    key = (doc.GetDocumentPath() or "", doc.GetDocumentName() or "",
           _scene_dirty(doc))
    hit = cache.get("scene")
    if hit is not None and hit.get("key") == key:
        adapter, tree = hit["adapter"], hit["tree"]
        adapter.doc = doc
        _refresh_selection(adapter, tree)
        return adapter, tree

    adapter = SceneAdapter(doc)
    phase = "Reading scene — %s" % label
    _progress(phase)
    tree = adapter.build_tree(
        progress=lambda cur, tot, name: _progress(phase, cur, tot, name))
    cache["scene"] = {"key": key, "adapter": adapter, "tree": tree}
    return adapter, tree


def invalidate_scene_cache() -> None:
    _cache_store().pop("scene", None)


def _scene_dirty(doc) -> int:
    try:
        return int(doc.GetDirty(c4d.DIRTYFLAGS_OBJECT | c4d.DIRTYFLAGS_DATA))
    except Exception:
        return 0


def _selection_info(doc) -> tuple:
    try:
        objs = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_SELECTIONORDER)
    except Exception:
        try:
            objs = doc.GetActiveObjects(0)
        except Exception:
            objs = []
    objs = objs or []
    names: list = []
    token = len(objs)
    for o in objs:
        try:
            nm = o.GetName()
            token = (token * 131 + hash((nm, o.GetType()))) & 0xFFFFFFFF
        except Exception:
            nm = ""
        if len(names) < 6:
            names.append(nm)
    return token, names, len(objs)


_OP_LABELS = {
    "analyze": "Analyzing scene",
    "export": "Exporting report",
    "export_csv": "Exporting CSV",
    "detect": "Detecting naming convention",
    "plan_naming": "Building rename preview",
    "apply_naming": "Applying renames",
    "plan_structure": "Building structure preview",
    "apply_structure": "Applying structure",
    "plan_layers": "Building layer preview",
    "apply_layers": "Assigning layers",
    "plan_layer_suggestions": "Suggesting layers",
    "apply_layer_suggestions": "Assigning suggested layers",
    "layer_mismatches": "Checking layer consistency",
    "delete_layer": "Deleting layer",
    "delete_empty_layers": "Deleting empty layers",
    "set_layer_colors": "Coloring layers",
    "plan_translate": "Building translation preview",
    "apply_translate": "Applying translations",
    "plan_all": "Planning all areas",
    "apply_all": "Applying everything",
    "apply_plan": "Applying restructuring plan",
    "revert_change": "Reverting change",
    "assign_layer": "Assigning layer",
    "move_to_group": "Moving objects to group",
    "focus": "Locating object",
    "focus_material": "Locating material",
    "rename_object": "Renaming object",
    "material_previews": "Rendering material previews",
    "texture_previews": "Rendering texture thumbnails",
    "fix_textures_relative": "Rewriting texture paths",
    "collect_textures": "Copying textures into the project",
    "relink_textures": "Relinking missing textures",
    "clear_missing_textures": "Clearing missing texture references",
    "set_texture_path": "Rewriting texture reference",
    "texture_resize": "Resizing textures",
    "texture_repath": "Rewriting texture paths",
    "pick_texture_path": "Waiting for the file picker (switch to Cinema 4D)",
    "files_pick_path": "Waiting for the file picker (switch to Cinema 4D)",
    "files_relink": "Relinking missing files",
    "pick_folder": "Waiting for the folder picker (switch to Cinema 4D)",
    "delete_material": "Deleting material",
    "delete_unused_materials": "Deleting unused materials",
    "perf_scan": "Measuring generator rebuild times",
}


_AUDIT_MODULES = {
    "tags": "audit_tags",
    "gens": "audit_generators",
    "files": "audit_files",
    "sims": "audit_sims",
    "perf": "audit_perf",
}


_MUTATING_OPS = {
    "apply_naming", "apply_structure", "apply_layers", "apply_translate",
    "apply_layer_suggestions",
    "apply_all", "apply_plan", "rename_object", "revert_change",
    "assign_layer", "move_to_group",
    "delete_layer", "delete_empty_layers", "set_layer_colors",
    "delete_material", "delete_unused_materials",
    "fix_textures_relative", "collect_textures", "relink_textures",
    "clear_missing_textures", "set_texture_path", "pick_texture_path",
    "texture_resize", "texture_repath",
    "tags_add_phong", "tags_set_phong_angle", "tags_delete_duplicates",
    "gens_apply", "sims_set_enabled", "files_make_relative",
    "files_pick_path", "files_relink",
}


def handle(payload: dict) -> dict:
    op = str(payload.get("op") or "")
    label = _OP_LABELS.get(op)
    if label is None and op.split("_", 1)[0] in _AUDIT_MODULES:
        label = "Scanning scene (%s)" % op.split("_", 1)[0]
    try:
        if label is not None:
            _progress(label)
        return _handle(payload)
    finally:
        if op in _MUTATING_OPS:
            invalidate_scene_cache()
        if label is not None:
            _clear_progress()


def _handle(payload: dict) -> dict:
    op = payload.get("op")
    settings = payload.get("settings", {})

    if op == "netinfo":
        return _netinfo(payload)

    doc = c4d.documents.GetActiveDocument()
    if doc is None:
        return {"error": "No active document."}

    if op == "dirty":
        sel_token, sel_names, sel_count = _selection_info(doc)
        return {"ok": True, "dirty": _scene_dirty(doc),
                "name": doc.GetDocumentName(),
                "sel": sel_token, "sel_names": sel_names, "sel_count": sel_count}

    if op == "ui_settings_get":
        from . import ui_settings as uimod
        ui = uimod.load_ui(DATA_DIR, doc.GetDocumentPath() or "",
                           doc.GetDocumentName() or "")
        return {"ok": True, "found": bool(ui), "ui": ui}

    if op == "ui_settings_set":
        from . import ui_settings as uimod
        res = uimod.save_ui(DATA_DIR, doc.GetDocumentPath() or "",
                            doc.GetDocumentName() or "", payload.get("ui") or {})
        return {"ok": bool(res.get("ok")), "path": res.get("path"),
                "error": res.get("error")}

    cfg, data = _load_cfg()

    if op in ("analyze", "export", "export_csv"):
        invalidate_scene_cache()
        adapter, tree = _get_scene(doc, "analyzing")
        _progress("Analyzing structure")
        scope = _scope(settings, adapter) if op == "analyze" else None
        if scope is not None and not scope:
            return {"error": "No objects selected in Cinema 4D."}
        include_hidden = (op != "analyze"
                          or bool(settings.get("include_hidden", False)))
        report = SceneAnalyzer(cfg.standard).analyze(
            tree, file_name=doc.GetDocumentName(), scope=scope,
            include_hidden=include_hidden)
        data_dict = report.to_dict()
        data_dict["scoped"] = scope is not None
        data_dict["include_hidden"] = include_hidden
        data_dict["dirty"] = _scene_dirty(doc)
        data_dict["doc_name"] = doc.GetDocumentName()
        data_dict["sel"] = _selection_info(doc)[0]
        try:
            full = os.path.join(doc.GetDocumentPath() or "", doc.GetDocumentName() or "")
            data_dict["file_size"] = os.path.getsize(full) if os.path.isfile(full) else 0
        except Exception:
            data_dict["file_size"] = 0
        try:
            _progress("Scanning materials")
            data_dict["materials"] = adapter.scan_materials(
                include_hidden=include_hidden,
                accepted=cfg.accepted_unused)
        except Exception:
            data_dict["materials"] = None
        try:
            _progress("Scanning textures")
            data_dict["textures"] = adapter.scan_textures(
                include_hidden=include_hidden,
                accepted=cfg.kept("textures"))
        except Exception as ex:  # noqa: BLE001
            import traceback
            data_dict["textures"] = None
            data_dict["textures_error"] = "%s: %s" % (
                type(ex).__name__, ex)
            data_dict["textures_trace"] = traceback.format_exc()[-1500:]
        try:
            _progress("Scanning layers")
            data_dict["layers_report"] = _merge_layers(
                data_dict, adapter.scan_layers(),
                all_object_counts=adapter._layer_object_counts())
        except Exception:
            data_dict["layers_report"] = None
        try:
            _progress("Checking generators & simulations")
            import importlib
            gens_mod = importlib.import_module(
                "sceneorg.cinema.audit_generators")
            sims_mod = importlib.import_module("sceneorg.cinema.audit_sims")
            data_dict["has_generators"] = gens_mod.has_any(adapter, tree)
            data_dict["has_sims"] = sims_mod.has_any(adapter, tree)
        except Exception:
            data_dict["has_generators"] = True
            data_dict["has_sims"] = True
        _progress("Writing report")

        import time
        now = time.time()
        data_dict["analyzed_ts"] = now
        data_dict["analyzed_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        if not data_dict.get("scoped"):
            _record_history(doc, {
                "file": data_dict.get("file") or "(unsaved)",
                "ts": now,
                "at": data_dict["analyzed_at"],
                "objects": data_dict.get("object_count", 0),
                "compliance": data_dict.get("structure_compliance", 0),
                "polys": data_dict.get("total_polys", 0),
                "size": data_dict.get("file_size", 0),
            })
        doc_dir = doc.GetDocumentPath() or None
        written = None if data_dict.get("scoped") else _write_export(data_dict, doc_dir)
        result = {"ok": True, "report": data_dict, "export_path": written}
        if op == "export_csv":
            csv_res = _write_csv(data_dict, doc_dir)
            result["csv_path"] = csv_res[0] if csv_res else None
            result["csv_rows"] = csv_res[1] if csv_res else 0
        return result

    if op == "history":
        return {"ok": True, "history": list(reversed(_read_history(doc)))}

    if op == "clear_history":
        # Write an empty log rather than deleting the file — an absent file
        # would fall back to the pre-split global log and resurrect the runs.
        try:
            with open(_history_path(doc), "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception as ex:
            return {"error": str(ex)}
        return {"ok": True}

    if op == "presets":
        return {"ok": True, "presets": _list_presets(),
                "active": data.get("preset")}

    if op == "apply_preset":
        return _apply_preset(payload.get("id", ""))

    if op == "save_preset":
        return _save_preset(payload.get("name", ""),
                            payload.get("description", ""),
                            overwrite=bool(payload.get("overwrite")))

    if op == "delete_preset":
        return _delete_preset(payload.get("id", ""))

    if op in ("plan_all", "apply_all"):
        adapter, tree = _get_scene(doc, "one-button plan")
        conv = _convention(settings, cfg)
        scope = _scope(settings, adapter)
        plan = pipeline.plan_combined(
            tree, cfg, convention=conv, scope=scope,
            safe_only=bool(settings.get("safe", True)),
            tidy=bool(settings.get("tidy", True)))
        result = {
            "ok": True,
            "naming": [{"guid": r.guid, "old": r.old_name, "new": r.new_name}
                       for r in plan.renames],
            "structure": [{"guid": r.guid, "name": r.name,
                           "from": r.from_group, "to": r.to_group}
                          for r in plan.reparents],
            "layers": [{"guid": o.guid, "name": o.name, "layer": o.layer}
                       for o in plan.layers],
            "applied_rules": plan.applied_rules,
            "warnings": plan.warnings,
            "total": plan.total,
            "preset": data.get("preset"),
        }
        if op == "apply_all":
            chosen = pipeline.filter_accepted(plan, payload.get("accept"))
            applied = adapter.apply_bundle(
                chosen.renames, chosen.reparents, chosen.layers,
                canonical=cfg.standard.canonical_group)
            result["applied"] = applied
            _record_change(
                "apply_all",
                "%d renamed, %d moved, %d layered" % (
                    applied["renames"], applied["reparents"], applied["layers"]),
                adapter.last_changes, doc=doc)
        return result

    if op == "plans":
        return {"ok": True, "plans": _list_plans()}

    if op == "apply_plan":
        plan = payload.get("plan")
        if plan is None and payload.get("id"):
            plan = _load_plan(payload["id"])
        if not plan or "operations" not in plan:
            return {"error": "no valid plan (need {operations:[...]})"}
        adapter, _ = _get_scene(doc, "restructuring plan")
        res = adapter.apply_plan(plan["operations"])
        _record_change("plan", "restructuring plan: %d ops" % res.get("total", 0),
                       [], revertible=False, doc=doc)
        return {"ok": True, **res}

    if op == "rename_object":
        adapter, _ = _get_scene(doc, "rename")
        new_name = str(payload.get("name") or "").strip()
        if not new_name:
            return {"ok": False, "error": "empty name"}
        ok = adapter.rename_object(payload.get("guid"), new_name)
        if ok:
            _record_change("naming", "renamed to “%s”" % new_name,
                           adapter.last_changes, doc=doc)
        return {"ok": ok, "applied": 1 if ok else 0}

    if op == "focus":
        adapter, _ = _get_scene(doc, "focus")
        ok = adapter.focus(payload.get("guid"))
        return {"ok": ok}

    if op == "type_icons":
        import base64
        import tempfile
        cache = _cache_store().setdefault("type_icons", {})
        tmp = os.path.join(tempfile.gettempdir(), "so_typeicon.png")
        icons = {}
        for tid in payload.get("ids") or []:
            try:
                tid = int(tid)
            except (TypeError, ValueError):
                continue
            if tid not in cache:
                data = ""
                try:
                    bmp = c4d.bitmaps.InitResourceBitmap(tid)
                    if bmp is not None and bmp.GetSize()[0] > 0 \
                            and bmp.Save(tmp, c4d.FILTER_PNG) == c4d.IMAGERESULT_OK:
                        with open(tmp, "rb") as f:
                            data = ("data:image/png;base64,"
                                    + base64.b64encode(f.read()).decode("ascii"))
                except Exception:
                    data = ""
                cache[tid] = data
            if cache[tid]:
                icons[str(tid)] = cache[tid]
        try:
            os.remove(tmp)
        except OSError:
            pass
        return {"ok": True, "icons": icons}

    if op == "material_previews":
        adapter = SceneAdapter(doc)
        size = int(payload.get("size") or 48)
        cache = _cache_store().setdefault("mat_previews", {})
        doc_key = doc.GetDocumentName() or ""
        names = payload.get("names") or []
        previews = {}
        missing = []
        for name in names:
            hit = cache.get((doc_key, name, size))
            if hit is not None:
                previews[name] = hit
            else:
                missing.append(name)
        if missing:
            fresh = adapter.material_previews(
                missing, size=size,
                progress=lambda cur, tot, nm: _progress(
                    "Rendering material previews", cur, tot, nm))
            for name, data in fresh.items():
                cache[(doc_key, name, size)] = data
            previews.update(fresh)
        return {"ok": True, "previews": previews}

    if op == "texture_previews":
        adapter = SceneAdapter(doc)
        size = int(payload.get("size") or 40)
        cache = _cache_store().setdefault("tex_previews", {})
        paths = payload.get("paths") or []
        previews = {}
        missing = []
        for p in paths:
            try:
                mtime = os.path.getmtime(p) if p and os.path.isfile(p) else 0
            except OSError:
                mtime = 0
            key = (p, mtime, size)
            hit = cache.get(key)
            if hit is not None:
                previews[p] = hit
            else:
                missing.append((p, key))
        if missing:
            fresh = adapter.texture_previews(
                [p for p, _ in missing], size=size,
                progress=lambda cur, tot, nm: _progress(
                    "Rendering texture thumbnails", cur, tot, nm))
            for p, key in missing:
                if p in fresh:
                    cache[key] = fresh[p]
                    previews[p] = fresh[p]
        return {"ok": True, "previews": previews}

    if op == "focus_material":
        adapter, _ = _get_scene(doc, "focus material")
        return {"ok": True, **adapter.focus_material(payload.get("name", ""))}

    if op == "delete_material":
        adapter = SceneAdapter(doc)
        name = payload.get("name", "")
        deleted = adapter.delete_material(
            name, include_hidden=bool(payload.get("include_hidden")))
        if deleted:
            _record_change("materials_delete", "deleted material '%s'" % name,
                           [], revertible=False, doc=doc)
        return {"ok": True, "deleted": deleted}

    if op == "delete_unused_materials":
        adapter = SceneAdapter(doc)
        deleted = adapter.delete_unused_materials(
            include_hidden=bool(payload.get("include_hidden")))
        if deleted:
            _record_change("materials_delete",
                           "deleted %d unused material(s)" % deleted,
                           [], revertible=False, doc=doc)
        return {"ok": True, "deleted": deleted}

    if op == "fix_textures_relative":
        adapter = SceneAdapter(doc)
        res = adapter.make_textures_relative(payload.get("materials"))
        if res.get("fixed"):
            _record_change("textures_relative",
                           "%d texture path(s) made relative" % res["fixed"],
                           [], revertible=False, doc=doc)
        return {"ok": True, **res}

    if op == "collect_textures":
        adapter = SceneAdapter(doc)
        res = adapter.collect_textures(payload.get("materials"),
                                       subdir=payload.get("subdir") or "tex")
        if res.get("relinked"):
            _record_change("textures_collect",
                           "%d texture(s) copied into the project, %d shader(s) relinked"
                           % (res.get("copied", 0), res["relinked"]),
                           [], revertible=False, doc=doc)
        return {"ok": True, **res}

    if op == "relink_textures":
        adapter = SceneAdapter(doc)
        res = adapter.relink_textures(payload.get("folder") or "",
                                      progress=_progress)
        if res.get("relinked"):
            _record_change("textures_relink",
                           "%d missing texture(s) relinked" % res["relinked"],
                           [], revertible=False, doc=doc)
        return {"ok": True, **res}

    if op == "open_file":
        p = str(payload.get("path") or "")
        if not p or not os.path.isfile(p):
            return {"error": "file not found: %s" % (p or "(empty)")}
        try:
            os.startfile(p)  # noqa: S606 - intentional, user-invoked
        except Exception as ex:  # noqa: BLE001
            return {"error": "could not open: %s" % ex}
        return {"ok": True}

    if op == "pick_texture_path":
        raw = str(payload.get("path") or "")
        try:
            chosen = c4d.storage.LoadDialog(
                type=c4d.FILESELECTTYPE_IMAGES,
                title="Pick replacement for %s" % os.path.basename(raw),
                flags=c4d.FILESELECT_LOAD,
                def_path=doc.GetDocumentPath() or "")
        except Exception as ex:  # noqa: BLE001
            return {"error": "file dialog failed: %s" % ex}
        if not chosen:
            return {"ok": True, "cancelled": True}
        adapter = SceneAdapter(doc)
        res = adapter.set_texture_path(raw, chosen,
                                       material=payload.get("material") or None)
        if res.get("changed"):
            _record_change("textures_edit",
                           "texture reference relinked to %s"
                           % os.path.basename(chosen),
                           [], revertible=False, doc=doc)
        return {"ok": True, "picked": chosen, **res}

    if op == "pick_folder":
        try:
            chosen = c4d.storage.LoadDialog(
                type=c4d.FILESELECTTYPE_ANYTHING,
                title=str(payload.get("title") or "Pick a folder"),
                flags=c4d.FILESELECT_DIRECTORY,
                def_path=doc.GetDocumentPath() or "")
        except Exception as ex:  # noqa: BLE001
            return {"error": "folder dialog failed: %s" % ex}
        return {"ok": True, "path": chosen or "", "cancelled": not chosen}

    if op == "set_texture_path":
        adapter = SceneAdapter(doc)
        res = adapter.set_texture_path(str(payload.get("path") or ""),
                                       str(payload.get("new_path") or ""),
                                       material=payload.get("material") or None)
        if res.get("changed"):
            what = "cleared" if not (payload.get("new_path") or "").strip() \
                else "rewritten"
            _record_change("textures_edit",
                           "texture reference %s (%s)" % (what,
                           os.path.basename(str(payload.get("path") or ""))),
                           [], revertible=False, doc=doc)
        return {"ok": True, **res}

    if op == "texture_repath":
        adapter = SceneAdapter(doc)
        mode = "absolute" if str(payload.get("mode")) == "absolute" else "relative"
        res = adapter.texture_repath(payload.get("paths") or [], mode=mode,
                                     material=payload.get("material") or None)
        if res.get("changed"):
            _record_change("textures_repath",
                           "%d texture path(s) made %s" % (res["changed"], mode),
                           adapter.last_changes, doc=doc)
        return {"ok": True, **res}

    if op == "texture_resize":
        adapter = SceneAdapter(doc)
        res = adapter.texture_resize(payload.get("paths") or [],
                                     payload.get("percent"))
        if res.get("error"):
            return {"ok": False, **res}
        if res.get("resized"):
            _record_change("textures_resize",
                           "%d texture(s) resized to %d%%, %d relinked"
                           % (res["resized"], int(payload.get("percent") or 0),
                              res.get("relinked", 0)),
                           adapter.last_changes, doc=doc)
        return {"ok": True, **res}

    if op == "clear_missing_textures":
        adapter = SceneAdapter(doc)
        res = adapter.clear_missing_textures()
        if res.get("cleared"):
            _record_change("textures_clear",
                           "%d missing texture reference(s) cleared" % res["cleared"],
                           [], revertible=False, doc=doc)
        return {"ok": True, **res}

    if op == "changes":
        return {"ok": True, "changes": list(reversed(_load_journal(doc)))}

    if op == "revert_change":
        entry_id = str(payload.get("id", ""))
        entries = _load_journal(doc)
        entry = next((e for e in entries if str(e.get("id")) == entry_id), None)
        if entry is None:
            return {"error": "change not found: %s" % entry_id}
        if entry.get("reverted"):
            return {"error": "already reverted"}
        if not entry.get("revertible"):
            return {"error": "this change cannot be reverted"}

        wanted = payload.get("items")
        pairs = journalmod.items_to_revert(entry, wanted)
        if not pairs:
            return {"ok": True, "reverted": 0, "missing": 0, "results": []}
        adapter, _ = _get_scene(doc, "revert")
        res = adapter.revert([it for _i, it in pairs],
                             canonical=cfg.standard.canonical_group)
        done = [pairs[k][0] for k, r in enumerate(res.get("results") or [])
                if r.get("status") == "reverted"]
        journalmod.mark_reverted(entry, done)
        journalmod.set_entry(entries, entry)
        _save_journal(doc, entries)
        return {"ok": True, **res}

    if op == "clear_changes":
        _save_journal(doc, [])
        return {"ok": True}

    if op in ("set_keeps", "set_keep_names", "set_accepted_unused"):
        section = {"set_keep_names": "naming",
                   "set_accepted_unused": "materials"}.get(
            op, str(payload.get("section", "")))
        keys = payload.get("keys", payload.get("names"))
        merged = cfgmod.migrate_config(_read_config_data())
        try:
            merged["keeps"] = keepsmod.set_section_keeps(
                merged.get("keeps"), section, keys or [])
        except ValueError as ex:
            return {"error": str(ex)}
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
        return {"ok": True, "section": section,
                "keys": merged["keeps"][section]}

    if op == "detect":
        _, tree = _get_scene(doc, "detect convention")
        res = detectmod.detect_convention([n.name for n in tree.walk()])
        return {"ok": True, "detect": {
            "style": res.style.value, "language": res.language,
            "number_pad": res.number_pad, "confidence": res.confidence,
            "casing_distribution": res.casing_distribution,
            "language_distribution": res.language_distribution,
        }}

    if op == "rules":
        return {"ok": True,
                "groups": [_rule_dict(r) for r in cfg.standard.rules],
                "structure": cfgmod.structure_to_list(cfg.standard),
                "rules": cfg.rules.to_list(),
                "rule_warnings": cfg.rules.warnings,
                "prefixes": cfg.prefixes,
                "convention": {
                    "style": cfg.convention.style.value,
                    "language": cfg.convention.language,
                    "number_pad": cfg.convention.number_pad,
                }}

    if op == "config":
        if payload.get("save"):
            with open(CONFIG_PATH, "w") as f:
                json.dump(payload.get("data", {}), f, indent=2, ensure_ascii=False)
            return {"ok": True, "saved": True, "path": CONFIG_PATH}
        return {"ok": True, "config": data, "defaults": cfgmod.DEFAULT_CONFIG}

    if op in ("plan_naming", "apply_naming"):
        adapter, tree = _get_scene(doc, "naming")
        conv = _convention(settings, cfg)
        scope = _scope(settings, adapter)
        # The web UI's eye toggle: hidden objects leave the rename worklist
        # (they keep their names and still block numbers/dedupe as siblings).
        # Default True so API callers without the flag keep planning everything.
        if not settings.get("include_hidden", True):
            visible = {n.guid for n in tree.walk() if n.visible}
            scope = visible if scope is None else (scope & visible)
        dedupe = bool(settings.get("dedupe", True))
        renames = ops.plan_renames(tree, conv, scope=scope,
                                   prefixes=cfg.prefixes, keep=cfg.keep_names,
                                   dedupe=dedupe)
        diff = [{"guid": r.guid, "old": r.old_name, "new": r.new_name,
                 "rules": r.rules} for r in renames]
        kept = sorted(cfg.kept("naming"))
        if op == "apply_naming":
            accepted = payload.get("guids")
            chosen = ([r for r in renames if r.guid in set(accepted)]
                      if accepted is not None else renames)
            applied = adapter.apply_renames(chosen)
            _record_change("naming", "%d renamed" % applied,
                           adapter.last_changes, doc=doc)
            return {"ok": True, "applied": applied, "count": len(chosen),
                    "diff": diff, "kept": kept, "keep_names": kept}
        return {"ok": True, "count": len(renames), "diff": diff,
                "kept": kept, "keep_names": kept}

    if op in ("plan_structure", "apply_structure"):
        adapter, tree = _get_scene(doc, "structure")
        scope = _scope(settings, adapter)
        safe = bool(settings.get("safe", True))
        tidy = bool(settings.get("tidy", True))
        reparents = ops.plan_reparents(tree, cfg.standard, scope=scope,
                                       safe_only=safe, tidy=tidy)
        reparents, kept = keepsmod.filter_kept(
            reparents, cfg.kept("structure"), key=lambda r: r.name)
        report = cfg.standard.evaluate(tree)
        in_scope = [f for f in report.misplaced if scope is None or f.guid in scope]
        skipped = max(0, len(in_scope) - len(reparents) - len(kept))
        diff = [{"guid": r.guid, "name": r.name, "from": r.from_group, "to": r.to_group}
                for r in reparents]
        if op == "apply_structure":
            accepted = payload.get("guids")
            chosen = (reparents if accepted is None else
                      [r for r in reparents if r.guid in set(accepted)])
            applied = adapter.apply_reparents(
                chosen, canonical=cfg.standard.canonical_group)
            _record_change("structure", "%d moved" % applied,
                           adapter.last_changes, doc=doc)
            return {"ok": True, "applied": applied, "count": len(chosen),
                    "diff": diff, "skipped": skipped, "kept": kept}
        return {"ok": True, "count": len(reparents), "diff": diff,
                "skipped": skipped, "kept": kept}

    if op in ("plan_translate", "apply_translate"):
        adapter, tree = _get_scene(doc, "translation")
        scope = _scope(settings, adapter)
        target = payload.get("target") or "en"
        engine = (payload.get("engine") or settings.get("engine")
                  or "offline").lower()
        if engine == "google":
            def _gprog(cur, tot):
                _progress("Translating online (Google)", cur, tot,
                          "%d / %d names" % (cur, tot))

            try:
                props, gerr, gdetected = _google_plan(tree, scope, target,
                                                      progress=_gprog)
            finally:
                _progress(_OP_LABELS.get(op, "Translating"))
            if gerr and not props:
                return {"error": "Google translate failed: %s" % gerr}
        else:
            gdetected = None
            props = translatemod.plan_translations(
                tree, scope=scope, target=target)
        props, kept = keepsmod.filter_kept(
            props, cfg.kept("translate"), key=lambda p: p.old)
        if op == "apply_translate":
            accepted = payload.get("guids")
            chosen = (props if accepted is None else
                      [p for p in props if p.guid in set(accepted)])
            renames = [ops.RenameOp(node=p.node, new_name=p.new) for p in chosen]
            applied = adapter.apply_renames(renames)
            _record_change("translate", "%d translated" % applied,
                           adapter.last_changes, doc=doc)
            return {"ok": True, "applied": applied, "count": len(renames)}
        diff = [{"guid": p.guid, "old": p.old, "new": p.new,
                 "words": p.words, "lang": p.lang} for p in props]
        if engine == "google" and gdetected and gdetected.get("total"):
            detected = gdetected
        else:
            detected = translatemod.detect_languages(tree, scope=scope).to_dict()
        return {"ok": True, "count": len(props), "diff": diff, "kept": kept,
                "target": target, "detected": detected, "engine": engine}

    if op in ("plan_layers", "apply_layers"):
        import collections
        adapter, tree = _get_scene(doc, "layers")
        scope = _scope(settings, adapter)
        layerops = ops.plan_layers(tree, scope=scope)
        layerops, kept = keepsmod.filter_kept(
            layerops, cfg.kept("layers"), key=lambda o: o.name)
        by_layer = dict(collections.Counter(o.layer for o in layerops))
        diff = [{"guid": o.guid, "name": o.name, "layer": o.layer} for o in layerops]
        if op == "apply_layers":
            accepted = payload.get("guids")
            chosen = layerops if accepted is None else [
                o for o in layerops if o.guid in set(accepted)]
            applied = adapter.apply_layers(chosen)
            _record_change("layers", "%d assigned to layers" % applied,
                           adapter.last_changes, doc=doc)
            return {"ok": True, "applied": applied, "count": len(chosen),
                    "diff": diff, "by_layer": by_layer, "kept": kept}
        return {"ok": True, "count": len(layerops), "diff": diff,
                "by_layer": by_layer, "kept": kept}

    if op == "plan_layer_suggestions":
        adapter, tree = _get_scene(doc, "layer suggestions")
        scope = _scope(settings, adapter)
        sugg = ops.plan_layer_suggestions(
            tree, scope=scope, keep=cfg.kept("layers"))
        diff = [{"guid": o.guid, "name": o.name, "layer": o.layer}
                for o in sugg]
        return {"ok": True, "count": len(sugg), "diff": diff}

    if op == "apply_layer_suggestions":
        adapter, tree = _get_scene(doc, "layer suggestions")
        scope = _scope(settings, adapter)
        sugg = ops.plan_layer_suggestions(
            tree, scope=scope, keep=cfg.kept("layers"))
        accepted = payload.get("guids")
        if accepted is not None:
            wanted = set(accepted)
            sugg = [o for o in sugg if o.guid in wanted]
        applied = adapter.apply_layers(sugg)
        _record_change("layers", "%d assigned to suggested layers" % applied,
                       adapter.last_changes, doc=doc)
        return {"ok": True, "applied": applied, "count": len(sugg)}

    if op == "layer_mismatches":
        _, tree = _get_scene(doc, "layer mismatches")
        found = layersmod.find_layer_mismatches(tree, keep=cfg.kept("layers"))
        return {"ok": True, "count": len(found),
                "findings": [f.to_dict() for f in found]}

    if op in ("delete_layer", "delete_empty_layers"):
        adapter, _ = _get_scene(doc, "delete layers")
        if op == "delete_layer":
            name = str(payload.get("name") or "").strip()
            if not name:
                return {"error": "missing layer name"}
            deleted = adapter.delete_layer(name)
            if deleted:
                _record_change("layers", "deleted layer %s" % name, [],
                               revertible=False,
                               doc=doc)
        else:
            keep = {str(n) for n in (payload.get("keep") or [])}
            deleted = adapter.delete_empty_layers(keep)
            if deleted:
                _record_change("layers", "%d empty layers deleted" % deleted,
                               [], revertible=False,
                               doc=doc)
        return {"ok": True, "deleted": deleted}

    if op == "set_layer_colors":
        adapter, _ = _get_scene(doc, "layer colors")
        colors: dict = {}
        for e in payload.get("colors") or []:
            name = str(e.get("name") or "").strip()
            col = e.get("color")
            if name and isinstance(col, (list, tuple)) and len(col) == 3:
                colors[name] = [max(0.0, min(1.0, float(c))) for c in col]
        if not colors:
            return {"error": "no layer colors given"}
        applied = adapter.set_layer_colors(colors)
        if applied:
            _record_change("layers", "%d layer colors set" % applied, [],
                           revertible=False, doc=doc)
        return {"ok": True, "applied": applied}

    if op in ("assign_layer", "move_to_group"):
        adapter, tree = _get_scene(doc, "batch action")
        key = "layer" if op == "assign_layer" else "group"
        target = str(payload.get(key) or "").strip()
        if not target:
            return {"error": "missing %s name" % key}
        guids = payload.get("guids") or []
        nodes = [n for n in (tree.find(g) for g in guids) if n is not None]
        if not nodes:
            return {"error": "no matching objects"}
        if op == "assign_layer":
            applied = adapter.apply_layers(
                [ops.LayerOp(node=n, layer=target) for n in nodes])
            _record_change("layers", "%d assigned to layer %s" % (applied, target),
                           adapter.last_changes, doc=doc)
            return {"ok": True, "applied": applied, "layer": target}
        reparents = [
            ops.ReparentOp(node=n, to_group=target,
                           from_group=n.parent.name if n.parent else "")
            for n in nodes]
        applied = adapter.apply_reparents(
            reparents, canonical=cfg.standard.canonical_group)
        _record_change("structure", "%d moved to %s" % (applied, target),
                       adapter.last_changes, doc=doc)
        return {"ok": True, "applied": applied, "group": target}

    prefix = op.split("_", 1)[0] if op else ""
    if prefix in _AUDIT_MODULES:
        import importlib
        mod = importlib.import_module(
            "sceneorg.cinema." + _AUDIT_MODULES[prefix])
        adapter, tree = _get_scene(doc, "%s audit" % prefix)
        return mod.handle(op, payload, doc=doc, adapter=adapter, tree=tree,
                          progress=_progress)

    return {"error": "unknown op: %s" % op}
