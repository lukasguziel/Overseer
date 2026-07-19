"""Blender JSON /api - the op registry, the Blender twin of cinema/webapi.py.

Hot-reloaded per request (see reload.py). Threads a ``BScene`` through every
handler where the C4D webapi threads a live ``doc``. Host-neutral IO (history,
export, google translate, config, netinfo) is delegated to
``overseer.core.webio``; per-project UI state reuses the host-neutral
``overseer.cinema.ui_settings`` (no ``c4d`` in it). Every handler returns the
SAME JSON shape as its C4D counterpart so the frozen frontend works unchanged.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

from .. import config as cfgmod
from ..core import journal as journalmod
from ..core import keeps as keepsmod
from ..core import layers as layersmod
from ..core import ops, webio
from ..core.analyzer import SceneAnalyzer
from ..naming import detect as detectmod
from ..naming import translate as translatemod
from ..naming import translations
from ..naming.casing import Casing
from ..naming.convention import NamingConvention
from . import host as bridge
from .adapter import SceneAdapter, load_journal, save_journal
from .scene import BScene

# Addon root = dir containing the ``overseer`` package (3 up from this file).
PLUGIN_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _prefs_base() -> str | None:
    try:
        import bpy
        return bpy.utils.user_resource("CONFIG")
    except Exception:
        return None


DATA_DIR = webio.resolve_data_dir(PLUGIN_DIR, _prefs_base())
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
EXPORT_PATH = os.path.join(DATA_DIR, "scene_report.json")
EXPORT_CSV_PATH = os.path.join(DATA_DIR, "scene_structure.csv")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
HISTORY_PATH = os.path.join(DATA_DIR, "analysis_history.json")
CHANGES_PATH = os.path.join(DATA_DIR, "change_history.json")
GOOGLE_CACHE_PATH = os.path.join(DATA_DIR, "google_cache.json")

webio.seed_config(PLUGIN_DIR, CONFIG_PATH)


# ---------------------------------------------------------------------------
# small local wrappers over webio (bind the fixed paths)
# ---------------------------------------------------------------------------
def _read_config_data() -> dict:
    return webio.read_config_data(CONFIG_PATH)


def _write_config_data(data: dict) -> None:
    webio.write_config_data(CONFIG_PATH, data)


def _slug(doc) -> str:
    from ..core import ui_settings_logic as uilogic
    return uilogic.project_slug(doc.path or "", doc.name or "") or "project"


def _history_path(doc) -> str:
    return webio.history_path(HISTORY_DIR, _slug(doc))


def _read_history(doc) -> list:
    return webio.read_history(_history_path(doc), HISTORY_PATH,
                              doc.name or "")


def _record_history(doc, entry: dict) -> None:
    webio.record_history(_history_path(doc), entry, HISTORY_PATH,
                         doc.name or "")


def _load_journal(doc) -> list:
    return load_journal(doc, CHANGES_PATH)


def _save_journal(doc, entries: list) -> None:
    save_journal(doc, entries[-webio.CHANGES_MAX:], CHANGES_PATH)


def _record_change(kind: str, summary: str, items: list,
                   revertible: bool = True, doc=None,
                   doc_name: str = "") -> dict | None:
    if not items and not summary:
        return None
    now = time.time()
    for it in (items or []):
        it.setdefault("reverted", False)
    entry = {
        "id": "%d" % int(now * 1000),
        "ts": now,
        "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "kind": kind,
        "summary": summary,
        "doc": doc_name or (doc.name if doc is not None else ""),
        "items": items or [],
        "revertible": bool(revertible and items),
        "reverted": False,
    }
    if doc is not None:
        entries = _load_journal(doc)
        entries.append(entry)
        _save_journal(doc, entries)
    return entry


def _merge_layers(report_dict: dict, layer_meta: list,
                  all_object_counts: dict | None = None) -> dict:
    return layersmod.build_layer_report(
        layer_meta,
        object_counts=dict(report_dict.get("layers_by_name") or {}),
        poly_counts=dict(report_dict.get("polys_by_layer") or {}),
        no_layer=report_dict.get("no_layer_count", 0),
        all_object_counts=all_object_counts)


# ---------------------------------------------------------------------------
# progress / netinfo
# ---------------------------------------------------------------------------
def _progress(phase, current=0, total=0, detail=""):
    bridge.set_progress(phase, current, total, detail)


def _clear_progress():
    bridge.clear_progress()


def _netinfo(payload: dict) -> dict:
    lan = bool(getattr(bridge, "lan_enabled", lambda: False)())
    changed = False
    if "listen_lan" in payload:
        data = _read_config_data()
        data["listen_lan"] = bool(payload["listen_lan"])
        _write_config_data(data)
        changed = data["listen_lan"] != lan
    port_fn = getattr(bridge, "server_port", None)
    port = (int(port_fn()) if port_fn
            else int(cfgmod.DEFAULT_CONFIG["port"]))
    return {"ok": True, "lan": lan,
            "wanted": bool(_read_config_data().get("listen_lan", False)),
            "restart_needed": changed, "ip": webio.lan_ip(), "port": port}


# ---------------------------------------------------------------------------
# config / convention / scope
# ---------------------------------------------------------------------------
def _load_cfg():
    data = _read_config_data()
    cfg = cfgmod.load_config(data)
    if cfg.extra_translations:
        translations.add_translations(cfg.extra_translations)
    return cfg, data


def _convention(settings: dict, cfg) -> NamingConvention:
    casing = settings.get("casing") or cfg.convention.style.value
    pad = int(settings.get("number_pad", cfg.convention.number_pad))
    return NamingConvention(
        style=Casing(casing), language=None, number_pad=pad,
        apply_numbering=bool(settings.get("apply_numbering", True)),
        apply_casing=bool(settings.get("apply_casing", True)),
        keep_separators=bool(settings.get("keep_separators", False)),
        keep_specials=bool(settings.get("keep_specials", True)))


def _scope(settings: dict, adapter: SceneAdapter):
    if settings.get("selection"):
        return adapter.selected_guids()
    return None


# ---------------------------------------------------------------------------
# scene cache (on the never-purged ``overseer`` package)
# ---------------------------------------------------------------------------
def _cache_store() -> dict:
    import overseer
    if not hasattr(overseer, "_scene_cache"):
        overseer._scene_cache = {}
    return overseer._scene_cache


def _refresh_selection(adapter, tree) -> None:
    adapter._selected_direct.clear()
    adapter._selected_subtree.clear()

    def visit(node, sel_ancestor):
        obj = adapter._by_guid.get(node.guid)
        is_sel = False
        if obj is not None:
            try:
                is_sel = bool(obj.select_get())
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
    key = (doc.path or "", doc.name or "", doc.dirty())
    hit = cache.get("scene")
    if hit is not None and hit.get("key") == key:
        adapter, tree = hit["adapter"], hit["tree"]
        adapter.doc = doc
        _refresh_selection(adapter, tree)
        return adapter, tree
    adapter = SceneAdapter(doc)
    phase = "Reading scene - %s" % label
    _progress(phase)
    tree = adapter.build_tree(
        progress=lambda cur, tot, name: _progress(phase, cur, tot, name))
    cache["scene"] = {"key": key, "adapter": adapter, "tree": tree}
    return adapter, tree


def invalidate_scene_cache() -> None:
    _cache_store().pop("scene", None)


# ---------------------------------------------------------------------------
# request object
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# doc-only handlers
# ---------------------------------------------------------------------------
def _op_dirty(payload: dict, doc) -> dict:
    sel_token, sel_names, sel_count = doc.selection_token()
    return {"ok": True, "dirty": doc.dirty(), "name": doc.name,
            "sel": sel_token, "sel_names": sel_names, "sel_count": sel_count}


def _op_ui_settings_get(payload: dict, doc) -> dict:
    from ..cinema import ui_settings as uimod
    ui = uimod.load_ui(DATA_DIR, doc.path or "", doc.name or "")
    return {"ok": True, "found": bool(ui), "ui": ui}


def _op_ui_settings_set(payload: dict, doc) -> dict:
    from ..cinema import ui_settings as uimod
    res = uimod.save_ui(DATA_DIR, doc.path or "", doc.name or "",
                        payload.get("ui") or {})
    return {"ok": bool(res.get("ok")), "path": res.get("path"),
            "error": res.get("error")}


# ---------------------------------------------------------------------------
# analyze / export
# ---------------------------------------------------------------------------
def _op_analyze(req: ApiRequest) -> dict:
    op, doc, cfg, settings = req.op, req.doc, req.cfg, req.settings
    invalidate_scene_cache()
    adapter, tree = _get_scene(doc, "analyzing")
    _progress("Analyzing structure")
    scope = _scope(settings, adapter) if op == "analyze" else None
    if scope is not None and not scope:
        return {"error": "No objects selected in Blender."}
    include_hidden = (op != "analyze"
                      or bool(settings.get("include_hidden", False)))
    report = SceneAnalyzer().analyze(
        tree, file_name=doc.name, scope=scope, include_hidden=include_hidden)
    data_dict = report.to_dict()
    data_dict["scoped"] = scope is not None
    data_dict["include_hidden"] = include_hidden
    data_dict["dirty"] = doc.dirty()
    data_dict["doc_name"] = doc.name
    data_dict["sel"] = doc.selection_token()[0]
    try:
        full = os.path.join(doc.path or "", doc.name or "")
        data_dict["file_size"] = os.path.getsize(full) if os.path.isfile(full) else 0
    except Exception:
        data_dict["file_size"] = 0
    try:
        _progress("Scanning materials")
        data_dict["materials"] = adapter.scan_materials(
            include_hidden=include_hidden, accepted=cfg.accepted_unused)
    except Exception:
        data_dict["materials"] = None
    try:
        _progress("Scanning textures")
        data_dict["textures"] = adapter.scan_textures(
            include_hidden=include_hidden, accepted=cfg.kept("textures"))
    except Exception as ex:  # noqa: BLE001
        import traceback
        data_dict["textures"] = None
        data_dict["textures_error"] = "%s: %s" % (type(ex).__name__, ex)
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
        gens_mod = importlib.import_module("overseer.blender.audit_generators")
        sims_mod = importlib.import_module("overseer.blender.audit_sims")
        data_dict["has_generators"] = gens_mod.has_any(adapter, tree)
        data_dict["has_sims"] = sims_mod.has_any(adapter, tree)
    except Exception:
        data_dict["has_generators"] = True
        data_dict["has_sims"] = True
    _progress("Writing report")

    now = time.time()
    data_dict["analyzed_ts"] = now
    data_dict["analyzed_at"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                             time.localtime(now))
    if not data_dict.get("scoped"):
        _record_history(doc, {
            "file": data_dict.get("file") or "(unsaved)", "ts": now,
            "at": data_dict["analyzed_at"],
            "objects": data_dict.get("object_count", 0),
            "polys": data_dict.get("total_polys", 0),
            "size": data_dict.get("file_size", 0)})
    doc_dir = doc.path or None
    written = (None if data_dict.get("scoped")
               else webio.write_export(data_dict, EXPORT_PATH, doc_dir))
    result = {"ok": True, "report": data_dict, "export_path": written}
    if op == "export_csv":
        csv_res = webio.write_csv(data_dict, EXPORT_CSV_PATH, doc_dir)
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


# ---------------------------------------------------------------------------
# naming / translate / layers / structure
# ---------------------------------------------------------------------------
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
    return {"ok": adapter.focus(req.payload.get("guid"))}


def _op_type_icons(req: ApiRequest) -> dict:
    # Blender object "types" are string enums, not numeric resource ids; the
    # tree renders fine without per-type PNGs. Return empty (UI degrades).
    return {"ok": True, "icons": {}}


def _op_detect(req: ApiRequest) -> dict:
    _, tree = _get_scene(req.doc, "detect convention")
    res = detectmod.detect_convention([n.name for n in tree.walk()])
    return {"ok": True, "detect": {
        "style": res.style.value, "language": res.language,
        "number_pad": res.number_pad, "confidence": res.confidence,
        "casing_distribution": res.casing_distribution,
        "language_distribution": res.language_distribution}}


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
    warning = None
    if engine == "google":
        def _gprog(cur, tot):
            _progress("Translating online (Google)", cur, tot,
                      "%d / %d names" % (cur, tot))
        try:
            props, gerr, gdetected = webio.google_plan(
                tree, scope, target, GOOGLE_CACHE_PATH, progress=_gprog)
        finally:
            _progress(_OP_LABELS.get(op, "Translating"))
        if gerr and not props:
            return {"error": "Google translate failed: %s" % gerr}
        if gerr:
            warning = ("Google translation was incomplete (%s). These "
                       "proposals come from the local cache; newly seen "
                       "names may be untranslated." % gerr)
    else:
        gdetected = None
        props = translatemod.plan_translations(tree, scope=scope, target=target)
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
    result = {"ok": True, "count": len(props), "diff": diff, "kept": kept,
              "target": target, "detected": detected, "engine": engine}
    if warning:
        result["warning"] = warning
    return result


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
    diff = [{"guid": o.guid, "name": o.name, "layer": o.layer}
            for o in layerops]
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
    sugg = ops.plan_layer_suggestions(tree, scope=scope, keep=cfg.kept("layers"))
    diff = [{"guid": o.guid, "name": o.name, "layer": o.layer} for o in sugg]
    return {"ok": True, "count": len(sugg), "diff": diff}


def _op_apply_layer_suggestions(req: ApiRequest) -> dict:
    payload, doc, cfg, settings = req.payload, req.doc, req.cfg, req.settings
    adapter, tree = _get_scene(doc, "layer suggestions")
    scope = _scope(settings, adapter)
    sugg = ops.plan_layer_suggestions(tree, scope=scope, keep=cfg.kept("layers"))
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
                           revertible=False, doc=doc)
    else:
        keep = {str(n) for n in (payload.get("keep") or [])}
        deleted = adapter.delete_empty_layers(keep)
        if deleted:
            _record_change("layers", "%d empty layers deleted" % deleted,
                           [], revertible=False, doc=doc)
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
    reparents = [ops.ReparentOp(node=n, to_group=target,
                                from_group=n.parent.name if n.parent else "")
                 for n in nodes]
    applied = adapter.apply_reparents(reparents)
    _record_change("structure", "%d moved to %s" % (applied, target),
                   adapter.last_changes, doc=doc)
    return {"ok": True, "applied": applied, "group": target}


# ---------------------------------------------------------------------------
# materials / textures (delegate to adapter mixins)
# ---------------------------------------------------------------------------
def _op_material_previews(req: ApiRequest) -> dict:
    payload, doc = req.payload, req.doc
    adapter = SceneAdapter(doc)
    size = int(payload.get("size") or 48)
    cache = _cache_store().setdefault("mat_previews", {})
    doc_key = doc.name or ""
    names = payload.get("names") or []
    previews, missing = {}, []
    for name in names:
        hit = cache.get((doc_key, name, size))
        if hit is not None:
            previews[name] = hit
        else:
            missing.append(name)
    if missing:
        fresh = adapter.material_previews(
            missing, size=size,
            progress=lambda c, t, nm: _progress(
                "Rendering material previews", c, t, nm))
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
    previews, missing = {}, []
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
            progress=lambda c, t, nm: _progress(
                "Rendering texture thumbnails", c, t, nm))
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
    payload, doc, cfg = req.payload, req.doc, req.cfg
    adapter = SceneAdapter(doc)
    deleted = adapter.delete_unused_materials(
        include_hidden=bool(payload.get("include_hidden")),
        accepted=cfg.accepted_unused)
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
    adapter = SceneAdapter(req.doc)
    return {"ok": True,
            **adapter.texture_owners(str(req.payload.get("path") or ""))}


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
        if hasattr(os, "startfile"):
            os.startfile(p)  # noqa: S606 - user-invoked
        else:
            import subprocess
            subprocess.Popen(["xdg-open", p])  # noqa: S603,S607
    except Exception as ex:  # noqa: BLE001
        return {"error": "could not open: %s" % ex}
    return {"ok": True}


def _op_pick_texture_path(req: ApiRequest) -> dict:
    # A blocking native file picker is not safely reachable from the pump
    # timer; the UI treats a cancel as a no-op. A dedicated modal operator
    # picker is a follow-up (see docs/ai/blender.md).
    return {"ok": True, "cancelled": True,
            "note": "Use Blender's file browser to relink, then rescan."}


def _op_pick_folder(req: ApiRequest) -> dict:
    return {"ok": True, "path": "", "cancelled": True,
            "note": "Folder picking from the web UI is not yet wired on Blender."}


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
                       "texture reference %s (%s)" % (
                           what, os.path.basename(str(payload.get("path") or ""))),
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
    doc, cfg = req.doc, req.cfg
    adapter = SceneAdapter(doc)
    res = adapter.clear_missing_textures(accepted=cfg.kept("textures"))
    if res.get("cleared"):
        _record_change("textures_clear",
                       "%d missing texture reference(s) cleared" % res["cleared"],
                       [], revertible=False, doc=doc)
    return {"ok": True, **res}


# ---------------------------------------------------------------------------
# change journal
# ---------------------------------------------------------------------------
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
    try:
        with open(CHANGES_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception:
        pass
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
    return {"ok": True, "section": section, "keys": merged["keeps"][section]}


# ---------------------------------------------------------------------------
# registries
# ---------------------------------------------------------------------------
_DOC_HANDLERS = {
    "dirty": _op_dirty,
    "ui_settings_get": _op_ui_settings_get,
    "ui_settings_set": _op_ui_settings_set,
}

_CFG_HANDLERS = {
    "analyze": _op_analyze, "export": _op_analyze, "export_csv": _op_analyze,
    "history": _op_history, "clear_history": _op_clear_history,
    "rename_object": _op_rename_object, "focus": _op_focus,
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
    "changes": _op_changes, "revert_change": _op_revert_change,
    "clear_changes": _op_clear_changes,
    "set_keeps": _op_set_keeps, "set_keep_names": _op_set_keeps,
    "set_accepted_unused": _op_set_keeps,
    "detect": _op_detect, "config": _op_config,
    "plan_naming": _op_plan_naming, "apply_naming": _op_plan_naming,
    "plan_translate": _op_plan_translate, "apply_translate": _op_plan_translate,
    "plan_layers": _op_plan_layers, "apply_layers": _op_plan_layers,
    "plan_layer_suggestions": _op_plan_layer_suggestions,
    "apply_layer_suggestions": _op_apply_layer_suggestions,
    "layer_mismatches": _op_layer_mismatches,
    "delete_layer": _op_delete_layers,
    "delete_empty_layers": _op_delete_layers,
    "set_layer_colors": _op_set_layer_colors,
    "assign_layer": _op_batch_assign, "move_to_group": _op_batch_assign,
}

_OP_LABELS = {
    "analyze": "Analyzing scene", "export": "Exporting report",
    "export_csv": "Exporting CSV", "detect": "Detecting naming convention",
    "plan_naming": "Building rename preview", "apply_naming": "Applying renames",
    "plan_layers": "Building layer preview", "apply_layers": "Assigning collections",
    "plan_layer_suggestions": "Suggesting collections",
    "apply_layer_suggestions": "Assigning suggested collections",
    "layer_mismatches": "Checking collection consistency",
    "delete_layer": "Deleting collection",
    "delete_empty_layers": "Deleting empty collections",
    "set_layer_colors": "Coloring collections",
    "plan_translate": "Building translation preview",
    "apply_translate": "Applying translations",
    "revert_change": "Reverting change", "assign_layer": "Assigning collection",
    "move_to_group": "Moving objects to group", "focus": "Locating object",
    "focus_material": "Locating material", "rename_object": "Renaming object",
    "material_previews": "Rendering material previews",
    "texture_previews": "Rendering texture thumbnails",
    "fix_textures_relative": "Rewriting texture paths",
    "texture_owners": "Finding materials using the texture",
    "collect_textures": "Copying textures into the project",
    "relink_textures": "Relinking missing textures",
    "clear_missing_textures": "Clearing missing texture references",
    "set_texture_path": "Rewriting texture reference",
    "texture_resize": "Resizing textures", "texture_repath": "Rewriting texture paths",
    "delete_material": "Deleting material",
    "delete_unused_materials": "Deleting unused materials",
    "perf_scan": "Measuring modifier rebuild times",
}

_AUDIT_MODULES = {
    "tags": "audit_tags", "gens": "audit_generators", "files": "audit_files",
    "sims": "audit_sims", "perf": "audit_perf",
}

_MUTATING_OPS = {
    "apply_naming", "apply_layers", "apply_translate", "apply_layer_suggestions",
    "rename_object", "revert_change", "assign_layer", "move_to_group",
    "delete_layer", "delete_empty_layers", "set_layer_colors",
    "delete_material", "delete_unused_materials", "fix_textures_relative",
    "collect_textures", "relink_textures", "clear_missing_textures",
    "set_texture_path", "pick_texture_path", "texture_resize", "texture_repath",
    "tags_add_phong", "tags_set_phong_angle", "tags_delete_duplicates",
    "gens_apply", "sims_set_enabled", "files_make_relative",
    "files_pick_path", "files_relink",
}


# ---------------------------------------------------------------------------
# dispatch
# ---------------------------------------------------------------------------
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

    doc = BScene.active()
    if doc is None:
        return {"error": "No active Blender scene."}

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
            "overseer.blender." + _AUDIT_MODULES[prefix])
        adapter, tree = _get_scene(doc, "%s audit" % prefix)
        return mod.handle(op, payload, doc=doc, adapter=adapter, tree=tree,
                          progress=_progress)

    return {"error": "unknown op: %s" % op}
