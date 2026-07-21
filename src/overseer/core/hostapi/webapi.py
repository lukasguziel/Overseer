"""The shared JSON /api op layer — written ONCE against the hostapi ports.

Every ``_op_*`` handler, the dispatch, and the IO/cache/progress/history/journal
plumbing live here and are host-neutral. A ``HostContext`` supplies the only
host-specific bits (active document, adapter factory, progress sink, bridge
facades, type icons, native pickers, per-area audits). ``build_handle(ctx)``
binds a context into that host's ``handle(payload)``.

This replaces the previously duplicated ``cinema/webapi.py`` and
``blender/webapi.py`` op registries. Both hosts now shrink to a context + a
one-line ``handle`` (see docs/ai/hostapi.md).
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

# hostapi is overseer.core.hostapi: ``..`` = overseer.core, ``...`` = overseer.
from ... import __version__ as APP_VERSION
from ... import config as cfgmod
from ... import updater as updatermod
from ...naming import detect as detectmod
from ...naming import translate as translatemod
from ...naming import translations
from ...naming.casing import Casing
from ...naming.convention import NamingConvention
from .. import defaults as cfgdefaults
from .. import journal as journalmod
from .. import keeps as keepsmod
from .. import layers as layersmod
from .. import ops, texthumbs, webio
from ..analyzer import SceneAnalyzer


@dataclass
class ApiRequest:
    op: str
    payload: dict
    doc: object = field(compare=False)          # a SceneHost
    cfg: cfgmod.Config = field(compare=False)
    data: dict = field(default_factory=dict)

    @property
    def settings(self) -> dict:
        return self.payload.get("settings", {})


_OP_LABELS = {
    "analyze": "Analyzing scene", "export": "Exporting report",
    "export_csv": "Exporting CSV", "detect": "Detecting naming convention",
    "plan_naming": "Building rename preview", "apply_naming": "Applying renames",
    "plan_layers": "Building layer preview", "apply_layers": "Assigning layers",
    "plan_layer_suggestions": "Suggesting layers",
    "apply_layer_suggestions": "Assigning suggested layers",
    "layer_mismatches": "Checking layer consistency",
    "delete_layer": "Deleting layer",
    "delete_empty_layers": "Deleting empty layers",
    "set_layer_colors": "Coloring layers",
    "plan_translate": "Building translation preview",
    "apply_translate": "Applying translations",
    "revert_change": "Reverting change", "assign_layer": "Assigning layer",
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
    "pick_texture_path": "Waiting for the file picker",
    "files_pick_path": "Waiting for the file picker",
    "files_relink": "Relinking missing files",
    "pick_folder": "Waiting for the folder picker",
    "delete_material": "Deleting material",
    "delete_unused_materials": "Deleting unused materials",
    "perf_scan": "Measuring generator rebuild times",
    "update_check": "Checking for updates",
    "update_install": "Downloading and installing the update",
}

_AUDIT_MODULES = {"tags", "gens", "files", "sims", "perf"}

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

_HISTORY_MAX = webio.HISTORY_MAX
_CHANGES_MAX = webio.CHANGES_MAX


class WebApi:
    """One instance per request (the module is hot-reloaded), bound to a
    ``HostContext``."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx
        self.PLUGIN_DIR = ctx.plugin_dir
        self.DATA_DIR = ctx.data_dir
        export_dir = getattr(ctx, "export_dir", None) or self.DATA_DIR
        self.CONFIG_PATH = os.path.join(self.DATA_DIR, "config.json")
        self.EXPORT_PATH = os.path.join(export_dir, "scene_report.json")
        self.EXPORT_CSV_PATH = os.path.join(export_dir, "scene_structure.csv")
        self.HISTORY_DIR = os.path.join(self.DATA_DIR, "history")
        self.HISTORY_PATH = os.path.join(self.DATA_DIR, "analysis_history.json")
        self.CHANGES_PATH = os.path.join(self.DATA_DIR, "change_history.json")
        self.GOOGLE_CACHE_PATH = os.path.join(self.DATA_DIR, "google_cache.json")
        webio.seed_config(self.PLUGIN_DIR, self.CONFIG_PATH)
        updatermod.confirm_ok(self._update_target())

        self._doc_handlers = {
            "dirty": self._op_dirty,
            "ui_settings_get": self._op_ui_settings_get,
            "ui_settings_set": self._op_ui_settings_set,
            "ui_global_get": self._op_ui_global_get,
            "ui_global_set": self._op_ui_global_set,
        }
        self._cfg_handlers = {
            "analyze": self._op_analyze, "export": self._op_analyze,
            "export_csv": self._op_analyze,
            "history": self._op_history, "clear_history": self._op_clear_history,
            "rename_object": self._op_rename_object, "focus": self._op_focus,
            "type_icons": self._op_type_icons,
            "material_previews": self._op_material_previews,
            "texture_previews": self._op_texture_previews,
            "focus_material": self._op_focus_material,
            "delete_material": self._op_delete_material,
            "delete_unused_materials": self._op_delete_unused_materials,
            "fix_textures_relative": self._op_fix_textures_relative,
            "texture_owners": self._op_texture_owners,
            "collect_textures": self._op_collect_textures,
            "relink_textures": self._op_relink_textures,
            "open_file": self._op_open_file,
            "pick_texture_path": self._op_pick_texture_path,
            "pick_folder": self._op_pick_folder,
            "set_texture_path": self._op_set_texture_path,
            "texture_repath": self._op_texture_repath,
            "texture_resize": self._op_texture_resize,
            "clear_missing_textures": self._op_clear_missing_textures,
            "changes": self._op_changes, "revert_change": self._op_revert_change,
            "clear_changes": self._op_clear_changes,
            "set_keeps": self._op_set_keeps, "set_keep_names": self._op_set_keeps,
            "set_accepted_unused": self._op_set_keeps,
            "detect": self._op_detect, "config": self._op_config,
            "plan_naming": self._op_plan_naming, "apply_naming": self._op_plan_naming,
            "plan_translate": self._op_plan_translate,
            "apply_translate": self._op_plan_translate,
            "plan_layers": self._op_plan_layers, "apply_layers": self._op_plan_layers,
            "plan_layer_suggestions": self._op_plan_layer_suggestions,
            "apply_layer_suggestions": self._op_apply_layer_suggestions,
            "layer_mismatches": self._op_layer_mismatches,
            "delete_layer": self._op_delete_layers,
            "delete_empty_layers": self._op_delete_layers,
            "set_layer_colors": self._op_set_layer_colors,
            "assign_layer": self._op_batch_assign,
            "move_to_group": self._op_batch_assign,
        }

    # -- progress -----------------------------------------------------------
    def _progress(self, phase, current=0, total=0, detail=""):
        self.ctx.progress(phase, current, total, detail)

    def _clear_progress(self):
        self.ctx.clear_progress()

    # -- config -------------------------------------------------------------
    def _read_config_data(self) -> dict:
        return webio.read_config_data(self.CONFIG_PATH)

    def _write_config_data(self, data: dict) -> None:
        webio.write_config_data(self.CONFIG_PATH, data)

    def _load_cfg(self):
        data = self._read_config_data()
        cfg = cfgmod.load_config(data)
        if cfg.extra_translations:
            translations.add_translations(cfg.extra_translations)
        return cfg, data

    # -- history / journal --------------------------------------------------
    def _slug(self, doc) -> str:
        from .. import ui_settings_logic as uilogic
        return uilogic.project_slug(doc.path or "", doc.name or "") or "project"

    def _history_path(self, doc) -> str:
        return webio.history_path(self.HISTORY_DIR, self._slug(doc))

    def _read_history(self, doc) -> list:
        return webio.read_history(self._history_path(doc), self.HISTORY_PATH,
                                  doc.name or "")

    def _record_history(self, doc, entry: dict) -> None:
        webio.record_history(self._history_path(doc), entry, self.HISTORY_PATH,
                             doc.name or "")

    def _load_journal(self, doc) -> list:
        return self.ctx.load_journal(doc, self.CHANGES_PATH)

    def _save_journal(self, doc, entries: list) -> None:
        self.ctx.save_journal(doc, entries[-_CHANGES_MAX:], self.CHANGES_PATH)

    def _record_change(self, kind, summary, items, revertible=True, doc=None,
                       doc_name=""):
        if not items and not summary:
            return None
        now = time.time()
        for it in (items or []):
            it.setdefault("reverted", False)
        entry = {
            "id": "%d" % int(now * 1000), "ts": now,
            "at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
            "kind": kind, "summary": summary,
            "doc": doc_name or (doc.name if doc is not None else ""),
            "items": items or [], "revertible": bool(revertible and items),
            "reverted": False,
        }
        if doc is not None:
            entries = self._load_journal(doc)
            entries.append(entry)
            self._save_journal(doc, entries)
        return entry

    def _merge_layers(self, report_dict, layer_meta, all_object_counts=None):
        return layersmod.build_layer_report(
            layer_meta,
            object_counts=dict(report_dict.get("layers_by_name") or {}),
            poly_counts=dict(report_dict.get("polys_by_layer") or {}),
            no_layer=report_dict.get("no_layer_count", 0),
            all_object_counts=all_object_counts)

    # -- scene cache (on the never-purged ``overseer`` package) -------------
    def _cache_store(self) -> dict:
        import overseer
        if not hasattr(overseer, "_scene_cache"):
            overseer._scene_cache = {}
        return overseer._scene_cache

    def _get_scene(self, doc, label: str):
        cache = self._cache_store()
        key = (doc.path or "", doc.name or "", doc.dirty())
        hit = cache.get("scene")
        if hit is not None and hit.get("key") == key:
            adapter, tree = hit["adapter"], hit["tree"]
            adapter.set_host(doc)
            adapter.refresh_selection(tree)
            return adapter, tree
        adapter = self.ctx.make_adapter(doc)
        phase = "Reading scene - %s" % label
        self._progress(phase)
        tree = adapter.build_tree(
            progress=lambda cur, tot, name: self._progress(phase, cur, tot, name))
        cache["scene"] = {"key": key, "adapter": adapter, "tree": tree}
        return adapter, tree

    def invalidate_scene_cache(self) -> None:
        self._cache_store().pop("scene", None)

    # -- helpers ------------------------------------------------------------
    def _convention(self, settings, cfg) -> NamingConvention:
        casing = settings.get("casing") or cfg.convention.style.value
        pad = int(settings.get("number_pad", cfg.convention.number_pad))
        return NamingConvention(
            style=Casing(casing), language=None, number_pad=pad,
            apply_numbering=bool(settings.get("apply_numbering", True)),
            apply_casing=bool(settings.get("apply_casing", True)),
            keep_separators=bool(settings.get("keep_separators", False)),
            keep_specials=bool(settings.get("keep_specials", True)))

    def _scope(self, settings, adapter):
        if settings.get("selection"):
            return adapter.selected_guids()
        return None

    # -- netinfo ------------------------------------------------------------
    def _netinfo(self, payload: dict) -> dict:
        lan = bool(self.ctx.lan_enabled())
        changed = False
        if "listen_lan" in payload:
            data = self._read_config_data()
            data["listen_lan"] = bool(payload["listen_lan"])
            self._write_config_data(data)
            changed = data["listen_lan"] != lan
        try:
            port = int(self.ctx.server_port())
        except Exception:
            port = int(cfgmod.DEFAULT_CONFIG["port"])
        return {"ok": True, "lan": lan,
                "wanted": bool(self._read_config_data().get("listen_lan", False)),
                "restart_needed": changed, "ip": webio.lan_ip(), "port": port}

    def _open_browser(self) -> dict:
        # Escape hatch for hosts whose embedded web view misbehaves (e.g. the
        # C4D 2026 HtmlViewer collapsing on resize): same UI, same local
        # server, just in the system browser. Doc-independent like netinfo.
        import webbrowser
        try:
            port = int(self.ctx.server_port())
        except Exception:
            port = int(cfgmod.DEFAULT_CONFIG["port"])
        try:
            ok = bool(webbrowser.open("http://127.0.0.1:%d/" % port))
        except Exception:
            ok = False
        return {"ok": ok}

    # -- auto-update (doc-independent, like netinfo) ------------------------
    def _update_target(self) -> updatermod.UpdateTarget:
        profile = dict(self.ctx.update_profile or {})
        return updatermod.UpdateTarget(
            repo=cfgdefaults.UPDATE_REPO, current_version=APP_VERSION,
            install_dir=self.PLUGIN_DIR, data_dir=self.DATA_DIR,
            asset_pattern=str(profile.get("asset_pattern") or ""),
            payload_marker=str(profile.get("payload_marker") or ""),
            disable_globs=tuple(profile.get("disable_globs") or ()))

    def _op_update_check(self, payload: dict) -> dict:
        import overseer
        target = self._update_target()
        out = {"ok": True, "host": self.ctx.host_label,
               "current": APP_VERSION, "repo": cfgdefaults.UPDATE_REPO,
               "supported": bool(target.asset_pattern),
               "state": updatermod.read_state(self.DATA_DIR)}
        if not target.asset_pattern:
            return out
        cache = getattr(overseer, "_update_cache", None)
        if not payload.get("force") and cache \
                and time.time() - cache.get("ts", 0) < updatermod.CHECK_TTL:
            result = cache["result"]
        else:
            result = updatermod.check(target)
            if result.get("ok"):
                overseer._update_cache = {"ts": time.time(), "result": result}
        if result.get("ok"):
            out.update({k: result[k] for k in
                        ("latest", "update_available", "writable", "releases")})
        else:
            out["check_failed"] = result.get("error") or "update check failed"
        return out

    def _op_update_install(self, payload: dict) -> dict:
        import overseer
        target = self._update_target()
        if not target.asset_pattern:
            return {"error": "updates are not supported on this host"}
        try:
            raw = updatermod.fetch_release_list(target.repo)
        except Exception as ex:  # noqa: BLE001
            return {"error": "update check failed: %s" % ex}
        fresh = updatermod.newer_releases(
            updatermod.parse_releases(raw, target.asset_pattern),
            target.current_version)
        if not fresh:
            return {"error": "no newer release found"}
        wanted = str(payload.get("version") or "")
        release = next((r for r in fresh if r.version == wanted),
                       None if wanted else fresh[0])
        if release is None:
            return {"error": "release %s not found" % wanted}

        def prog(stage, done=0, total=0):
            if stage == "download":
                self._progress("Downloading update", done, total,
                               release.asset_name)
            else:
                self._progress("Installing update")

        out = updatermod.install(target, release, progress=prog)
        if out.get("ok"):
            overseer._update_cache = None
            out["host"] = self.ctx.host_label
        return out

    def _op_update_ack(self, payload: dict) -> dict:
        updatermod.acknowledge(self.DATA_DIR)
        return {"ok": True}

    # -- doc-only handlers --------------------------------------------------
    def _op_dirty(self, payload, doc) -> dict:
        sel_token, sel_names, sel_count = doc.selection_token()
        return {"ok": True, "dirty": doc.dirty(), "name": doc.name,
                "sel": sel_token, "sel_names": sel_names, "sel_count": sel_count}

    def _op_ui_settings_get(self, payload, doc) -> dict:
        from .. import ui_settings_io as uimod
        ui = uimod.load_ui(self.DATA_DIR, doc.path or "", doc.name or "")
        return {"ok": True, "found": bool(ui), "ui": ui}

    def _op_ui_settings_set(self, payload, doc) -> dict:
        from .. import ui_settings_io as uimod
        res = uimod.save_ui(self.DATA_DIR, doc.path or "", doc.name or "",
                            payload.get("ui") or {})
        return {"ok": bool(res.get("ok")), "path": res.get("path"),
                "error": res.get("error")}

    def _op_ui_global_get(self, payload, doc) -> dict:
        from .. import ui_settings_io as uimod
        return {"ok": True, "ui": uimod.load_global_ui(self.DATA_DIR)}

    def _op_ui_global_set(self, payload, doc) -> dict:
        from .. import ui_settings_io as uimod
        res = uimod.save_global_ui(self.DATA_DIR, payload.get("ui") or {})
        return {"ok": bool(res.get("ok")), "error": res.get("error")}

    # -- analyze / export ---------------------------------------------------
    def _op_analyze(self, req: ApiRequest) -> dict:
        op, doc, cfg, settings = req.op, req.doc, req.cfg, req.settings
        self.invalidate_scene_cache()
        adapter, tree = self._get_scene(doc, "analyzing")
        self._progress("Analyzing structure")
        scope = self._scope(settings, adapter) if op == "analyze" else None
        if scope is not None and not scope:
            return {"error": "No objects selected."}
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
            self._progress("Scanning materials")
            data_dict["materials"] = adapter.scan_materials(
                include_hidden=include_hidden, accepted=cfg.accepted_unused)
        except Exception:
            data_dict["materials"] = None
        try:
            self._progress("Scanning textures")
            data_dict["textures"] = adapter.scan_textures(
                include_hidden=include_hidden, accepted=cfg.kept("textures"))
        except Exception as ex:  # noqa: BLE001
            import traceback
            data_dict["textures"] = None
            data_dict["textures_error"] = "%s: %s" % (type(ex).__name__, ex)
            data_dict["textures_trace"] = traceback.format_exc()[-1500:]
        try:
            self._progress("Scanning layers")
            data_dict["layers_report"] = self._merge_layers(
                data_dict, adapter.scan_layers(),
                all_object_counts=adapter._layer_object_counts())
        except Exception:
            data_dict["layers_report"] = None
        try:
            self._progress("Checking generators & simulations")
            gens_mod = self.ctx.audit("gens")
            sims_mod = self.ctx.audit("sims")
            data_dict["has_generators"] = gens_mod.has_any(adapter, tree)
            data_dict["has_sims"] = sims_mod.has_any(adapter, tree)
        except Exception:
            data_dict["has_generators"] = True
            data_dict["has_sims"] = True
        self._progress("Writing report")

        now = time.time()
        data_dict["analyzed_ts"] = now
        data_dict["analyzed_at"] = time.strftime("%Y-%m-%d %H:%M:%S",
                                                 time.localtime(now))
        if not data_dict.get("scoped"):
            self._record_history(doc, {
                "file": data_dict.get("file") or "(unsaved)", "ts": now,
                "at": data_dict["analyzed_at"],
                "objects": data_dict.get("object_count", 0),
                "polys": data_dict.get("total_polys", 0),
                "size": data_dict.get("file_size", 0)})
        doc_dir = doc.path or None
        written = (None if data_dict.get("scoped")
                   else webio.write_export(data_dict, self.EXPORT_PATH, doc_dir))
        result = {"ok": True, "report": data_dict, "export_path": written}
        if op == "export_csv":
            csv_res = webio.write_csv(data_dict, self.EXPORT_CSV_PATH, doc_dir)
            result["csv_path"] = csv_res[0] if csv_res else None
            result["csv_rows"] = csv_res[1] if csv_res else 0
        return result

    def _op_history(self, req) -> dict:
        return {"ok": True, "history": list(reversed(self._read_history(req.doc)))}

    def _op_clear_history(self, req) -> dict:
        try:
            with open(self._history_path(req.doc), "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception as ex:
            return {"error": str(ex)}
        return {"ok": True}

    # -- naming / translate / layers / structure ----------------------------
    def _op_rename_object(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter, _ = self._get_scene(doc, "rename")
        new_name = str(payload.get("name") or "").strip()
        if not new_name:
            return {"ok": False, "error": "empty name"}
        ok = adapter.rename_object(payload.get("guid"), new_name)
        if ok:
            self._record_change("naming", "renamed to “%s”" % new_name,
                                adapter.last_changes, doc=doc)
        return {"ok": ok, "applied": 1 if ok else 0}

    def _op_focus(self, req) -> dict:
        adapter, _ = self._get_scene(req.doc, "focus")
        return {"ok": adapter.focus(req.payload.get("guid"))}

    def _op_type_icons(self, req) -> dict:
        return {"ok": True, "icons": self.ctx.type_icons(req.payload.get("ids") or [])}

    def _op_detect(self, req) -> dict:
        _, tree = self._get_scene(req.doc, "detect convention")
        res = detectmod.detect_convention([n.name for n in tree.walk()])
        return {"ok": True, "detect": {
            "style": res.style.value, "language": res.language,
            "number_pad": res.number_pad, "confidence": res.confidence,
            "casing_distribution": res.casing_distribution,
            "language_distribution": res.language_distribution}}

    def _op_config(self, req) -> dict:
        payload, data = req.payload, req.data
        if payload.get("save"):
            with open(self.CONFIG_PATH, "w") as f:
                json.dump(payload.get("data", {}), f, indent=2, ensure_ascii=False)
            return {"ok": True, "saved": True, "path": self.CONFIG_PATH}
        return {"ok": True, "config": data, "defaults": cfgmod.DEFAULT_CONFIG}

    def _op_plan_naming(self, req) -> dict:
        op, payload, doc, cfg = req.op, req.payload, req.doc, req.cfg
        settings = req.settings
        adapter, tree = self._get_scene(doc, "naming")
        conv = self._convention(settings, cfg)
        scope = self._scope(settings, adapter)
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
            self._record_change("naming", "%d renamed" % applied,
                                adapter.last_changes, doc=doc)
            return {"ok": True, "applied": applied, "count": len(chosen),
                    "diff": diff, "kept": kept, "keep_names": kept}
        return {"ok": True, "count": len(renames), "diff": diff,
                "kept": kept, "keep_names": kept}

    def _op_plan_translate(self, req) -> dict:
        op, payload, doc, cfg = req.op, req.payload, req.doc, req.cfg
        settings = req.settings
        adapter, tree = self._get_scene(doc, "translation")
        scope = self._scope(settings, adapter)
        target = payload.get("target") or "en"
        engine = (payload.get("engine") or settings.get("engine")
                  or "offline").lower()
        warning = None
        if engine == "google":
            def _gprog(cur, tot):
                self._progress("Translating online (Google)", cur, tot,
                               "%d / %d names" % (cur, tot))
            try:
                props, gerr, gdetected = webio.google_plan(
                    tree, scope, target, self.GOOGLE_CACHE_PATH, progress=_gprog)
            finally:
                self._progress(_OP_LABELS.get(op, "Translating"))
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
            self._record_change("translate", "%d translated" % applied,
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

    def _op_plan_layers(self, req) -> dict:
        import collections
        op, payload, doc, cfg = req.op, req.payload, req.doc, req.cfg
        settings = req.settings
        adapter, tree = self._get_scene(doc, "layers")
        scope = self._scope(settings, adapter)
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
            self._record_change("layers", "%d assigned to layers" % applied,
                                adapter.last_changes, doc=doc)
            return {"ok": True, "applied": applied, "count": len(chosen),
                    "diff": diff, "by_layer": by_layer, "kept": kept}
        return {"ok": True, "count": len(layerops), "diff": diff,
                "by_layer": by_layer, "kept": kept}

    def _op_plan_layer_suggestions(self, req) -> dict:
        doc, cfg, settings = req.doc, req.cfg, req.settings
        adapter, tree = self._get_scene(doc, "layer suggestions")
        scope = self._scope(settings, adapter)
        sugg = ops.plan_layer_suggestions(tree, scope=scope, keep=cfg.kept("layers"))
        diff = [{"guid": o.guid, "name": o.name, "layer": o.layer} for o in sugg]
        return {"ok": True, "count": len(sugg), "diff": diff}

    def _op_apply_layer_suggestions(self, req) -> dict:
        payload, doc, cfg, settings = req.payload, req.doc, req.cfg, req.settings
        adapter, tree = self._get_scene(doc, "layer suggestions")
        scope = self._scope(settings, adapter)
        sugg = ops.plan_layer_suggestions(tree, scope=scope, keep=cfg.kept("layers"))
        accepted = payload.get("guids")
        if accepted is not None:
            wanted = set(accepted)
            sugg = [o for o in sugg if o.guid in wanted]
        applied = adapter.apply_layers(sugg)
        self._record_change("layers", "%d assigned to suggested layers" % applied,
                            adapter.last_changes, doc=doc)
        return {"ok": True, "applied": applied, "count": len(sugg)}

    def _op_layer_mismatches(self, req) -> dict:
        _, tree = self._get_scene(req.doc, "layer mismatches")
        found = layersmod.find_layer_mismatches(tree, keep=req.cfg.kept("layers"))
        return {"ok": True, "count": len(found),
                "findings": [f.to_dict() for f in found]}

    def _op_delete_layers(self, req) -> dict:
        op, payload, doc = req.op, req.payload, req.doc
        adapter, _ = self._get_scene(doc, "delete layers")
        if op == "delete_layer":
            name = str(payload.get("name") or "").strip()
            if not name:
                return {"error": "missing layer name"}
            deleted = adapter.delete_layer(name)
            if deleted:
                self._record_change("layers", "deleted layer %s" % name, [],
                                    revertible=False, doc=doc)
        else:
            keep = {str(n) for n in (payload.get("keep") or [])}
            deleted = adapter.delete_empty_layers(keep)
            if deleted:
                self._record_change("layers", "%d empty layers deleted" % deleted,
                                    [], revertible=False, doc=doc)
        return {"ok": True, "deleted": deleted}

    def _op_set_layer_colors(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter, _ = self._get_scene(doc, "layer colors")
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
            self._record_change("layers", "%d layer colors set" % applied, [],
                                revertible=False, doc=doc)
        return {"ok": True, "applied": applied}

    def _op_batch_assign(self, req) -> dict:
        op, payload, doc = req.op, req.payload, req.doc
        adapter, tree = self._get_scene(doc, "batch action")
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
            self._record_change("layers", "%d assigned to layer %s" % (applied, target),
                                adapter.last_changes, doc=doc)
            return {"ok": True, "applied": applied, "layer": target}
        reparents = [ops.ReparentOp(node=n, to_group=target,
                                    from_group=n.parent.name if n.parent else "")
                     for n in nodes]
        applied = adapter.apply_reparents(reparents)
        self._record_change("structure", "%d moved to %s" % (applied, target),
                            adapter.last_changes, doc=doc)
        return {"ok": True, "applied": applied, "group": target}

    # -- materials / textures ----------------------------------------------
    def _op_material_previews(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        size = int(payload.get("size") or 48)
        cache = self._cache_store().setdefault("mat_previews", {})
        doc_key = doc.name or ""
        names = payload.get("names") or []
        previews, missing = {}, []
        # Materials whose preview never materializes are remembered with the
        # dirty token they failed at and NOT retried until the scene actually
        # changes: rendering a preview can bump the host's dirty counter, and
        # a retry on every fetch would feed the frontend's scene watcher an
        # endless refresh loop.
        dirty = doc.dirty()
        for name in names:
            hit = cache.get((doc_key, name, size))
            if hit is not None:
                previews[name] = hit
            elif cache.get(("failed", doc_key, name, size)) != dirty:
                missing.append(name)
        if missing:
            fresh = adapter.material_previews(
                missing, size=size,
                progress=lambda c, t, nm: self._progress(
                    "Rendering material previews", c, t, nm))
            for name, data in fresh.items():
                cache[(doc_key, name, size)] = data
            # Stamp failures with the POST-render token — if the render
            # itself bumped dirty, the next fetch still counts as tried.
            failed_dirty = doc.dirty()
            for name in missing:
                if name not in fresh:
                    cache[("failed", doc_key, name, size)] = failed_dirty
            previews.update(fresh)
        return {"ok": True, "previews": previews}

    def _op_texture_previews(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        size = int(payload.get("size") or 40)
        cache = self._cache_store().setdefault("tex_previews", {})
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
        # Pillow first — thread-safe and independent of the host bitmap
        # engine (the C4D bridge answers these on the server thread already;
        # here it covers Blender and any path that slipped past the bridge).
        still = []
        for p, key in missing:
            uri = texthumbs.thumbnail(p, size)
            if uri is not None:
                cache[key] = uri
                previews[p] = uri
            else:
                still.append((p, key))
        if still:
            fresh = adapter.texture_previews(
                [p for p, _ in still], size=size,
                progress=lambda c, t, nm: self._progress(
                    "Rendering texture thumbnails", c, t, nm))
            for p, key in still:
                if p in fresh:
                    cache[key] = fresh[p]
                    previews[p] = fresh[p]
        return {"ok": True, "previews": previews}

    def _op_focus_material(self, req) -> dict:
        adapter, _ = self._get_scene(req.doc, "focus material")
        return {"ok": True, **adapter.focus_material(req.payload.get("name", ""))}

    def _op_delete_material(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        name = payload.get("name", "")
        deleted = adapter.delete_material(
            name, include_hidden=bool(payload.get("include_hidden")))
        if deleted:
            self._record_change("materials_delete", "deleted material '%s'" % name,
                                [], revertible=False, doc=doc)
        return {"ok": True, "deleted": deleted}

    def _op_delete_unused_materials(self, req) -> dict:
        payload, doc, cfg = req.payload, req.doc, req.cfg
        adapter = self.ctx.make_adapter(doc)
        deleted = adapter.delete_unused_materials(
            include_hidden=bool(payload.get("include_hidden")),
            accepted=cfg.accepted_unused)
        if deleted:
            self._record_change("materials_delete",
                                "deleted %d unused material(s)" % deleted,
                                [], revertible=False, doc=doc)
        return {"ok": True, "deleted": deleted}

    def _op_fix_textures_relative(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        res = adapter.make_textures_relative(payload.get("materials"))
        if res.get("fixed"):
            self._record_change("textures_relative",
                                "%d texture path(s) made relative" % res["fixed"],
                                [], revertible=False, doc=doc)
        return {"ok": True, **res}

    def _op_texture_owners(self, req) -> dict:
        adapter = self.ctx.make_adapter(req.doc)
        return {"ok": True,
                **adapter.texture_owners(str(req.payload.get("path") or ""))}

    def _op_collect_textures(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        res = adapter.collect_textures(payload.get("materials"),
                                       subdir=payload.get("subdir") or "tex",
                                       paths=payload.get("paths"))
        if res.get("relinked"):
            self._record_change(
                "textures_collect",
                "%d texture(s) copied into the project, %d reference(s) relinked"
                % (res.get("copied", 0), res["relinked"]), [], revertible=False,
                doc=doc)
        return {"ok": True, **res}

    def _op_relink_textures(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        res = adapter.relink_textures(payload.get("folder") or "",
                                      progress=self._progress)
        if res.get("relinked"):
            self._record_change("textures_relink",
                                "%d missing texture(s) relinked" % res["relinked"],
                                [], revertible=False, doc=doc)
        return {"ok": True, **res}

    def _op_open_file(self, req) -> dict:
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

    def _op_pick_texture_path(self, req) -> dict:
        # The native picker is host-specific; the relink + journal record are
        # shared. ctx returns {"picked": path} | {"cancelled": True} | {"error"}.
        payload, doc = req.payload, req.doc
        picked = self.ctx.pick_texture_path(payload, doc)
        if picked.get("error"):
            return picked
        chosen = picked.get("picked") or picked.get("path")
        if picked.get("cancelled") or not chosen:
            return {"ok": True, "cancelled": True}
        adapter = self.ctx.make_adapter(doc)
        res = adapter.set_texture_path(str(payload.get("path") or ""), chosen,
                                       material=payload.get("material") or None)
        if res.get("changed"):
            self._record_change(
                "textures_edit",
                "texture reference relinked to %s" % os.path.basename(chosen),
                [], revertible=False, doc=doc)
        return {"ok": True, "picked": chosen, **res}

    def _op_pick_folder(self, req) -> dict:
        return self.ctx.pick_folder(req.payload, req.doc)

    def _op_set_texture_path(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        res = adapter.set_texture_path(str(payload.get("path") or ""),
                                       str(payload.get("new_path") or ""),
                                       material=payload.get("material") or None)
        if res.get("changed"):
            what = "cleared" if not (payload.get("new_path") or "").strip() \
                else "rewritten"
            self._record_change(
                "textures_edit", "texture reference %s (%s)" % (
                    what, os.path.basename(str(payload.get("path") or ""))),
                [], revertible=False, doc=doc)
        return {"ok": True, **res}

    def _op_texture_repath(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        mode = "absolute" if str(payload.get("mode")) == "absolute" else "relative"
        res = adapter.texture_repath(payload.get("paths") or [], mode=mode,
                                     material=payload.get("material") or None)
        if res.get("changed"):
            self._record_change("textures_repath",
                                "%d texture path(s) made %s" % (res["changed"], mode),
                                adapter.last_changes, doc=doc)
        return {"ok": True, **res}

    def _op_texture_resize(self, req) -> dict:
        payload, doc = req.payload, req.doc
        adapter = self.ctx.make_adapter(doc)
        res = adapter.texture_resize(payload.get("paths") or [],
                                     payload.get("percent"))
        if res.get("error"):
            return {"ok": False, **res}
        if res.get("resized"):
            self._record_change("textures_resize",
                                "%d texture(s) resized to %d%%, %d relinked"
                                % (res["resized"], int(payload.get("percent") or 0),
                                   res.get("relinked", 0)),
                                adapter.last_changes, doc=doc)
        return {"ok": True, **res}

    def _op_clear_missing_textures(self, req) -> dict:
        doc, cfg = req.doc, req.cfg
        adapter = self.ctx.make_adapter(doc)
        res = adapter.clear_missing_textures(accepted=cfg.kept("textures"))
        if res.get("cleared"):
            self._record_change("textures_clear",
                                "%d missing texture reference(s) cleared" % res["cleared"],
                                [], revertible=False, doc=doc)
        return {"ok": True, **res}

    # -- change journal -----------------------------------------------------
    def _op_changes(self, req) -> dict:
        return {"ok": True, "changes": list(reversed(self._load_journal(req.doc)))}

    def _op_revert_change(self, req) -> dict:
        payload, doc = req.payload, req.doc
        entry_id = str(payload.get("id", ""))
        entries = self._load_journal(doc)
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
        adapter, _ = self._get_scene(doc, "revert")
        res = adapter.revert([it for _i, it in pairs])
        done = [pairs[k][0] for k, r in enumerate(res.get("results") or [])
                if r.get("status") == "reverted"]
        journalmod.mark_reverted(entry, done)
        journalmod.set_entry(entries, entry)
        self._save_journal(doc, entries)
        return {"ok": True, **res}

    def _op_clear_changes(self, req) -> dict:
        self._save_journal(req.doc, [])
        try:
            with open(self.CHANGES_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception:
            pass
        return {"ok": True}

    def _op_set_keeps(self, req) -> dict:
        op, payload = req.op, req.payload
        section = {"set_keep_names": "naming",
                   "set_accepted_unused": "materials"}.get(
            op, str(payload.get("section", "")))
        keys = payload.get("keys", payload.get("names"))
        merged = cfgmod.migrate_config(self._read_config_data())
        try:
            merged["keeps"] = keepsmod.set_section_keeps(
                merged.get("keeps"), section, keys or [])
        except ValueError as ex:
            return {"error": str(ex)}
        self._write_config_data(merged)
        return {"ok": True, "section": section, "keys": merged["keeps"][section]}

    # -- dispatch -----------------------------------------------------------
    def handle(self, payload: dict) -> dict:
        op = str(payload.get("op") or "")
        label = _OP_LABELS.get(op)
        if label is None and op.split("_", 1)[0] in _AUDIT_MODULES:
            label = "Scanning scene (%s)" % op.split("_", 1)[0]
        try:
            if label is not None:
                self._progress(label)
            return self._handle(payload)
        finally:
            if op in _MUTATING_OPS:
                self.invalidate_scene_cache()
            if label is not None:
                self._clear_progress()

    def _handle(self, payload: dict) -> dict:
        op = str(payload.get("op") or "")
        if op == "netinfo":
            return self._netinfo(payload)
        if op == "open_browser":
            return self._open_browser()
        if op == "update_check":
            return self._op_update_check(payload)
        if op == "update_install":
            return self._op_update_install(payload)
        if op == "update_ack":
            return self._op_update_ack(payload)

        doc = self.ctx.active_host()
        if doc is None:
            return {"error": "No active document."}

        doc_handler = self._doc_handlers.get(op)
        if doc_handler is not None:
            return doc_handler(payload, doc)

        cfg, data = self._load_cfg()
        handler = self._cfg_handlers.get(op)
        if handler is not None:
            return handler(ApiRequest(op=op, payload=payload, doc=doc,
                                      cfg=cfg, data=data))

        prefix = op.split("_", 1)[0]
        if prefix in _AUDIT_MODULES:
            mod = self.ctx.audit(prefix)
            if mod is None:
                return {"error": "unknown op: %s" % op}
            adapter, tree = self._get_scene(doc, "%s audit" % prefix)
            # Audits receive the doc reference the ADAPTER works on: the SceneHost
            # for Blender (its audits use ``doc.undo_push``), the raw c4d document
            # for Cinema (its audits use ``doc.StartUndo``). ``adapter.doc`` is
            # exactly that per host.
            return mod.handle(op, payload, doc=adapter.doc, adapter=adapter,
                              tree=tree, progress=self._progress)

        return {"error": "unknown op: %s" % op}


def build_handle(ctx):
    """Bind a HostContext into that host's ``handle(payload)`` function."""
    return WebApi(ctx).handle
