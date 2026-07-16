from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import c4d

from .. import config as cfgmod
from ..core import journal as journalmod
from ..core import keeps as keepsmod
from ..core import layers as layersmod
from ..core import ops
from ..core.analyzer import SceneAnalyzer
from ..naming import detect as detectmod
from ..naming import translate as translatemod
from ..naming import translations
from ..naming.casing import Casing
from ..naming.convention import NamingConvention
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
    path = os.path.join(base, "overseer")

    legacy = os.path.join(base, "scene_organizer")
    if not os.path.isdir(path) and os.path.isdir(legacy):
        try:
            os.rename(legacy, path)
        except OSError:
            path = legacy
    os.makedirs(path, exist_ok=True)
    return path


def _export_dir() -> str:
    env = os.environ.get("OVERSEER_EXPORT_DIR")
    if env and os.path.isdir(env):
        return env
    try:
        stamp = os.path.join(PLUGIN_DIR, "dev_repo.txt")
        if os.path.isfile(stamp):
            with open(stamp, encoding="utf-8-sig") as f:
                repo = f.read().strip()
            if repo and os.path.isdir(repo):
                var = os.path.join(repo, "var")
                os.makedirs(var, exist_ok=True)
                return var
    except OSError:
        pass
    return DATA_DIR


DATA_DIR = _user_data_dir()
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

EXPORT_PATH = os.path.join(_export_dir(), "scene_report.json")
EXPORT_CSV_PATH = os.path.join(_export_dir(), "scene_structure.csv")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
HISTORY_PATH = os.path.join(DATA_DIR, "analysis_history.json")
CHANGES_PATH = os.path.join(DATA_DIR, "change_history.json")
GOOGLE_CACHE_PATH = os.path.join(DATA_DIR, "google_cache.json")

_HISTORY_MAX = 100
_CHANGES_MAX = 200
_GCACHE_MAX = 20000

_CSV_FIELDS = ("path", "name", "type", "category", "depth", "casing",
               "language", "children")

if DATA_DIR != PLUGIN_DIR:
    _seed = os.path.join(PLUGIN_DIR, "config.json")
    if os.path.isfile(_seed) and not os.path.isfile(CONFIG_PATH):
        import shutil
        try:
            shutil.copy2(_seed, CONFIG_PATH)
        except OSError:
            pass


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


def _write_config_data(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _lan_ip():
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
    from .. import bridge
    lan = bool(getattr(bridge, "lan_enabled", lambda: False)())
    changed = False
    if "listen_lan" in payload:
        data = _read_config_data()
        data["listen_lan"] = bool(payload["listen_lan"])
        _write_config_data(data)
        changed = data["listen_lan"] != lan
    port_fn = getattr(bridge, "server_port", None)
    port = (int(port_fn()) if port_fn
            else int(getattr(bridge, "DEFAULT_PORT",
                             cfgmod.DEFAULT_CONFIG["port"])))
    return {"ok": True,
            "lan": lan,
            "wanted": bool(_read_config_data().get("listen_lan", False)),
            "restart_needed": changed,
            "ip": _lan_ip(),
            "port": port}


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
        c4d.StatusSetText("Overseer: %s" % phase)
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
    import overseer
    if not hasattr(overseer, "_scene_cache"):
        overseer._scene_cache = {}
    return overseer._scene_cache


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


@dataclass
class ApiRequest:
    op: str
    payload: dict
    doc: object = field(compare=False)
    cfg: cfgmod.Config = field(compare=False)
    data: dict = field(default_factory=dict)

    @property
    def settings(self) -> dict:
        return self.payload.get("settings", {})


def _op_dirty(payload: dict, doc) -> dict:
    sel_token, sel_names, sel_count = _selection_info(doc)
    return {"ok": True, "dirty": _scene_dirty(doc),
            "name": doc.GetDocumentName(),
            "sel": sel_token, "sel_names": sel_names, "sel_count": sel_count}


def _op_ui_settings_get(payload: dict, doc) -> dict:
    from . import ui_settings as uimod
    ui = uimod.load_ui(DATA_DIR, doc.GetDocumentPath() or "",
                       doc.GetDocumentName() or "")
    return {"ok": True, "found": bool(ui), "ui": ui}


def _op_ui_settings_set(payload: dict, doc) -> dict:
    from . import ui_settings as uimod
    res = uimod.save_ui(DATA_DIR, doc.GetDocumentPath() or "",
                        doc.GetDocumentName() or "", payload.get("ui") or {})
    return {"ok": bool(res.get("ok")), "path": res.get("path"),
            "error": res.get("error")}


def _op_analyze(req: ApiRequest) -> dict:
    op, doc, cfg, settings = req.op, req.doc, req.cfg, req.settings
    invalidate_scene_cache()
    adapter, tree = _get_scene(doc, "analyzing")
    _progress("Analyzing structure")
    scope = _scope(settings, adapter) if op == "analyze" else None
    if scope is not None and not scope:
        return {"error": "No objects selected in Cinema 4D."}
    include_hidden = (op != "analyze"
                      or bool(settings.get("include_hidden", False)))
    report = SceneAnalyzer().analyze(
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
            "overseer.cinema.audit_generators")
        sims_mod = importlib.import_module("overseer.cinema.audit_sims")
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


def _op_history(req: ApiRequest) -> dict:
    return {"ok": True, "history": list(reversed(_read_history(req.doc)))}


def _op_clear_history(req: ApiRequest) -> dict:
    try:
        with open(_history_path(req.doc), "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception as ex:
        return {"error": str(ex)}
    return {"ok": True}


def _op_rename_object(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter, _ = _get_scene(doc, "rename")
    new_name = str(payload.get("name") or "").strip()
    if not new_name:
        return {"ok": False, "error": "empty name"}
    ok = adapter.rename_object(payload.get("guid"), new_name)
    if ok:
        _record_change("naming", "renamed to “%s”" % new_name,
                       adapter.last_changes, doc=doc)
    return {"ok": ok, "applied": 1 if ok else 0}


def _op_focus(req: ApiRequest) -> dict:
    adapter, _ = _get_scene(req.doc, "focus")
    ok = adapter.focus(req.payload.get("guid"))
    return {"ok": ok}


def _op_type_icons(req: ApiRequest) -> dict:
    import base64
    import tempfile
    cache = _cache_store().setdefault("type_icons", {})
    tmp = os.path.join(tempfile.gettempdir(), "so_typeicon.png")
    icons = {}
    for tid in req.payload.get("ids") or []:
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


def _op_material_previews(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
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


def _op_texture_previews(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
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


def _op_focus_material(req: ApiRequest) -> dict:
    adapter, _ = _get_scene(req.doc, "focus material")
    return {"ok": True, **adapter.focus_material(req.payload.get("name", ""))}


def _op_delete_material(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter = SceneAdapter(doc)
    name = payload.get("name", "")
    deleted = adapter.delete_material(
        name, include_hidden=bool(payload.get("include_hidden")))
    if deleted:
        _record_change("materials_delete", "deleted material '%s'" % name,
                       [], revertible=False, doc=doc)
    return {"ok": True, "deleted": deleted}


def _op_delete_unused_materials(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter = SceneAdapter(doc)
    deleted = adapter.delete_unused_materials(
        include_hidden=bool(payload.get("include_hidden")))
    if deleted:
        _record_change("materials_delete",
                       "deleted %d unused material(s)" % deleted,
                       [], revertible=False, doc=doc)
    return {"ok": True, "deleted": deleted}


def _op_fix_textures_relative(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter = SceneAdapter(doc)
    res = adapter.make_textures_relative(payload.get("materials"))
    if res.get("fixed"):
        _record_change("textures_relative",
                       "%d texture path(s) made relative" % res["fixed"],
                       [], revertible=False, doc=doc)
    return {"ok": True, **res}


def _op_texture_owners(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter = SceneAdapter(doc)
    return {"ok": True,
            **adapter.texture_owners(str(payload.get("path") or ""))}


def _op_collect_textures(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter = SceneAdapter(doc)
    res = adapter.collect_textures(payload.get("materials"),
                                   subdir=payload.get("subdir") or "tex",
                                   paths=payload.get("paths"))
    if res.get("relinked"):
        _record_change("textures_collect",
                       "%d texture(s) copied into the project, %d reference(s) relinked"
                       % (res.get("copied", 0), res["relinked"]),
                       [], revertible=False, doc=doc)
    return {"ok": True, **res}


def _op_relink_textures(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter = SceneAdapter(doc)
    res = adapter.relink_textures(payload.get("folder") or "",
                                  progress=_progress)
    if res.get("relinked"):
        _record_change("textures_relink",
                       "%d missing texture(s) relinked" % res["relinked"],
                       [], revertible=False, doc=doc)
    return {"ok": True, **res}


def _op_open_file(req: ApiRequest) -> dict:
    p = str(req.payload.get("path") or "")
    if not p or not os.path.isfile(p):
        return {"error": "file not found: %s" % (p or "(empty)")}
    try:
        os.startfile(p)  # noqa: S606 - intentional, user-invoked
    except Exception as ex:  # noqa: BLE001
        return {"error": "could not open: %s" % ex}
    return {"ok": True}


def _op_pick_texture_path(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
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


def _op_pick_folder(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    try:
        chosen = c4d.storage.LoadDialog(
            type=c4d.FILESELECTTYPE_ANYTHING,
            title=str(payload.get("title") or "Pick a folder"),
            flags=c4d.FILESELECT_DIRECTORY,
            def_path=doc.GetDocumentPath() or "")
    except Exception as ex:  # noqa: BLE001
        return {"error": "folder dialog failed: %s" % ex}
    return {"ok": True, "path": chosen or "", "cancelled": not chosen}


def _op_set_texture_path(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
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


def _op_texture_repath(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter = SceneAdapter(doc)
    mode = "absolute" if str(payload.get("mode")) == "absolute" else "relative"
    res = adapter.texture_repath(payload.get("paths") or [], mode=mode,
                                 material=payload.get("material") or None)
    if res.get("changed"):
        _record_change("textures_repath",
                       "%d texture path(s) made %s" % (res["changed"], mode),
                       adapter.last_changes, doc=doc)
    return {"ok": True, **res}


def _op_texture_resize(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
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


def _op_clear_missing_textures(req: ApiRequest) -> dict:
    doc = req.doc
    adapter = SceneAdapter(doc)
    res = adapter.clear_missing_textures()
    if res.get("cleared"):
        _record_change("textures_clear",
                       "%d missing texture reference(s) cleared" % res["cleared"],
                       [], revertible=False, doc=doc)
    return {"ok": True, **res}


def _op_changes(req: ApiRequest) -> dict:
    return {"ok": True, "changes": list(reversed(_load_journal(req.doc)))}


def _op_revert_change(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
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
    res = adapter.revert([it for _i, it in pairs])
    done = [pairs[k][0] for k, r in enumerate(res.get("results") or [])
            if r.get("status") == "reverted"]
    journalmod.mark_reverted(entry, done)
    journalmod.set_entry(entries, entry)
    _save_journal(doc, entries)
    return {"ok": True, **res}


def _op_clear_changes(req: ApiRequest) -> dict:
    _save_journal(req.doc, [])
    return {"ok": True}


def _op_set_keeps(req: ApiRequest) -> dict:
    op, payload = req.op, req.payload
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
    _write_config_data(merged)
    return {"ok": True, "section": section,
            "keys": merged["keeps"][section]}


def _op_detect(req: ApiRequest) -> dict:
    _, tree = _get_scene(req.doc, "detect convention")
    res = detectmod.detect_convention([n.name for n in tree.walk()])
    return {"ok": True, "detect": {
        "style": res.style.value, "language": res.language,
        "number_pad": res.number_pad, "confidence": res.confidence,
        "casing_distribution": res.casing_distribution,
        "language_distribution": res.language_distribution,
    }}


def _op_config(req: ApiRequest) -> dict:
    payload, data = req.payload, req.data
    if payload.get("save"):
        with open(CONFIG_PATH, "w") as f:
            json.dump(payload.get("data", {}), f, indent=2, ensure_ascii=False)
        return {"ok": True, "saved": True, "path": CONFIG_PATH}
    return {"ok": True, "config": data, "defaults": cfgmod.DEFAULT_CONFIG}


def _op_plan_naming(req: ApiRequest) -> dict:
    op, payload, doc, cfg = req.op, req.payload, req.doc, req.cfg
    settings = req.settings
    adapter, tree = _get_scene(doc, "naming")
    conv = _convention(settings, cfg)
    scope = _scope(settings, adapter)
    if not settings.get("include_hidden", True):
        visible = {n.guid for n in tree.walk() if n.visible}
        scope = visible if scope is None else (scope & visible)
    dedupe = bool(settings.get("dedupe", True))
    renames = ops.plan_renames(tree, conv, scope=scope, keep=cfg.keep_names,
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


def _op_plan_translate(req: ApiRequest) -> dict:
    op, payload, doc, cfg = req.op, req.payload, req.doc, req.cfg
    settings = req.settings
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


def _op_plan_layers(req: ApiRequest) -> dict:
    import collections
    op, payload, doc, cfg = req.op, req.payload, req.doc, req.cfg
    settings = req.settings
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


def _op_plan_layer_suggestions(req: ApiRequest) -> dict:
    doc, cfg, settings = req.doc, req.cfg, req.settings
    adapter, tree = _get_scene(doc, "layer suggestions")
    scope = _scope(settings, adapter)
    sugg = ops.plan_layer_suggestions(
        tree, scope=scope, keep=cfg.kept("layers"))
    diff = [{"guid": o.guid, "name": o.name, "layer": o.layer}
            for o in sugg]
    return {"ok": True, "count": len(sugg), "diff": diff}


def _op_apply_layer_suggestions(req: ApiRequest) -> dict:
    payload, doc, cfg, settings = req.payload, req.doc, req.cfg, req.settings
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


def _op_layer_mismatches(req: ApiRequest) -> dict:
    _, tree = _get_scene(req.doc, "layer mismatches")
    found = layersmod.find_layer_mismatches(tree, keep=req.cfg.kept("layers"))
    return {"ok": True, "count": len(found),
            "findings": [f.to_dict() for f in found]}


def _op_delete_layers(req: ApiRequest) -> dict:
    op, payload, doc = req.op, req.payload, req.doc
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


def _op_set_layer_colors(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
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


def _op_batch_assign(req: ApiRequest) -> dict:
    op, payload, doc = req.op, req.payload, req.doc
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
    applied = adapter.apply_reparents(reparents)
    _record_change("structure", "%d moved to %s" % (applied, target),
                   adapter.last_changes, doc=doc)
    return {"ok": True, "applied": applied, "group": target}


_DOC_HANDLERS = {
    "dirty": _op_dirty,
    "ui_settings_get": _op_ui_settings_get,
    "ui_settings_set": _op_ui_settings_set,
}

_CFG_HANDLERS = {
    "analyze": _op_analyze,
    "export": _op_analyze,
    "export_csv": _op_analyze,
    "history": _op_history,
    "clear_history": _op_clear_history,
    "rename_object": _op_rename_object,
    "focus": _op_focus,
    "type_icons": _op_type_icons,
    "material_previews": _op_material_previews,
    "texture_previews": _op_texture_previews,
    "focus_material": _op_focus_material,
    "delete_material": _op_delete_material,
    "delete_unused_materials": _op_delete_unused_materials,
    "fix_textures_relative": _op_fix_textures_relative,
    "texture_owners": _op_texture_owners,
    "collect_textures": _op_collect_textures,
    "relink_textures": _op_relink_textures,
    "open_file": _op_open_file,
    "pick_texture_path": _op_pick_texture_path,
    "pick_folder": _op_pick_folder,
    "set_texture_path": _op_set_texture_path,
    "texture_repath": _op_texture_repath,
    "texture_resize": _op_texture_resize,
    "clear_missing_textures": _op_clear_missing_textures,
    "changes": _op_changes,
    "revert_change": _op_revert_change,
    "clear_changes": _op_clear_changes,
    "set_keeps": _op_set_keeps,
    "set_keep_names": _op_set_keeps,
    "set_accepted_unused": _op_set_keeps,
    "detect": _op_detect,
    "config": _op_config,
    "plan_naming": _op_plan_naming,
    "apply_naming": _op_plan_naming,
    "plan_translate": _op_plan_translate,
    "apply_translate": _op_plan_translate,
    "plan_layers": _op_plan_layers,
    "apply_layers": _op_plan_layers,
    "plan_layer_suggestions": _op_plan_layer_suggestions,
    "apply_layer_suggestions": _op_apply_layer_suggestions,
    "layer_mismatches": _op_layer_mismatches,
    "delete_layer": _op_delete_layers,
    "delete_empty_layers": _op_delete_layers,
    "set_layer_colors": _op_set_layer_colors,
    "assign_layer": _op_batch_assign,
    "move_to_group": _op_batch_assign,
}

_OP_LABELS = {
    "analyze": "Analyzing scene",
    "export": "Exporting report",
    "export_csv": "Exporting CSV",
    "detect": "Detecting naming convention",
    "plan_naming": "Building rename preview",
    "apply_naming": "Applying renames",
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
    "revert_change": "Reverting change",
    "assign_layer": "Assigning layer",
    "move_to_group": "Moving objects to group",
    "focus": "Locating object",
    "focus_material": "Locating material",
    "rename_object": "Renaming object",
    "material_previews": "Rendering material previews",
    "texture_previews": "Rendering texture thumbnails",
    "fix_textures_relative": "Rewriting texture paths",
    "texture_owners": "Finding materials using the texture",
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
    "apply_naming", "apply_layers", "apply_translate",
    "apply_layer_suggestions",
    "rename_object", "revert_change",
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
    op = str(payload.get("op") or "")

    if op == "netinfo":
        return _netinfo(payload)

    doc = c4d.documents.GetActiveDocument()
    if doc is None:
        return {"error": "No active document."}

    doc_handler = _DOC_HANDLERS.get(op)
    if doc_handler is not None:
        return doc_handler(payload, doc)

    cfg, data = _load_cfg()
    handler = _CFG_HANDLERS.get(op)
    if handler is not None:
        return handler(ApiRequest(op=op, payload=payload, doc=doc,
                                  cfg=cfg, data=data))

    prefix = op.split("_", 1)[0]
    if prefix in _AUDIT_MODULES:
        import importlib
        mod = importlib.import_module(
            "overseer.cinema." + _AUDIT_MODULES[prefix])
        adapter, tree = _get_scene(doc, "%s audit" % prefix)
        return mod.handle(op, payload, doc=doc, adapter=adapter, tree=tree,
                          progress=_progress)

    return {"error": "unknown op: %s" % op}
