"""JSON API of the web frontend (c4d-dependent, runs on the main thread).

Freshly reloaded by bridge.drain() on every request (hot-reload).
Uses exclusively the pure sceneorg logic + the c4d_adapter.
"""

from __future__ import annotations

import json
import os

import c4d

from . import config as cfgmod
from . import detect as detectmod
from . import graph as graphmod
from . import ops, translations
from . import translate as translatemod
from .analyzer import SceneAnalyzer
from .c4d_adapter import SceneAdapter
from .convention import NamingConvention
from .naming import Casing

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PLUGIN_DIR, "config.json")
PRESETS_DIR = os.path.join(PLUGIN_DIR, "presets")
# Restructuring plans learned/written by the skill.
PLANS_DIR = os.path.join(PLUGIN_DIR, "plans")

# Full report additionally lands in the repo -> Claude reads it directly.
EXPORT_PATH = r"C:\Users\lukas\code\cinema4d\scene-organizer\scene_report.json"
EXPORT_CSV_PATH = r"C:\Users\lukas\code\cinema4d\scene-organizer\scene_structure.csv"
# Analysis history (which project when) lives next to config.json in the plugin.
HISTORY_PATH = os.path.join(PLUGIN_DIR, "analysis_history.json")
_HISTORY_MAX = 100

# Columns of the flat CSV structure (one object per row).
_CSV_FIELDS = ("path", "name", "type", "category", "depth", "casing",
               "language", "children")


def _write_export(report_dict) -> str | None:
    try:
        d = os.path.dirname(EXPORT_PATH)
        if not os.path.isdir(d):
            return None
        with open(EXPORT_PATH, "w") as f:
            json.dump(report_dict, f, ensure_ascii=True, indent=1)
        return EXPORT_PATH
    except Exception:
        return None


def _write_csv(report_dict) -> tuple[str, int] | None:
    """Flat node table (path;name;type;...) for Excel/Sheets.

    Uses semicolon as delimiter (German Excel locale) and writes a header
    row. Returns (path, row count) or None on error.
    """
    import csv
    try:
        d = os.path.dirname(EXPORT_CSV_PATH)
        if not os.path.isdir(d):
            return None
        nodes = report_dict.get("nodes", [])
        with open(EXPORT_CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=_CSV_FIELDS, delimiter=";",
                               extrasaction="ignore")
            w.writeheader()
            for n in nodes:
                w.writerow(n)
        return EXPORT_CSV_PATH, len(nodes)
    except Exception:
        return None


def _record_history(entry: dict) -> None:
    """Appends an analysis entry (file/when/objects) to the history.

    Debounced: the same file within 60 s only updates the last entry instead
    of spamming (live preview/refresh trigger multiple times).
    """
    try:
        hist = []
        if os.path.isfile(HISTORY_PATH):
            with open(HISTORY_PATH, encoding="utf-8") as f:
                hist = json.load(f) or []
        last = hist[-1] if hist else None
        if (last and last.get("file") == entry.get("file")
                and abs(entry["ts"] - last.get("ts", 0)) < 60):
            hist[-1] = entry
        else:
            hist.append(entry)
        hist = hist[-_HISTORY_MAX:]
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(hist, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _read_history() -> list:
    try:
        if os.path.isfile(HISTORY_PATH):
            with open(HISTORY_PATH, encoding="utf-8") as f:
                return json.load(f) or []
    except Exception:
        pass
    return []


def _read_config_data() -> dict:
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _list_presets() -> list:
    """All presets (presets/*.json) with their meta info."""
    out = []
    try:
        for fn in sorted(os.listdir(PRESETS_DIR)):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(PRESETS_DIR, fn), encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("meta", {})
                out.append({
                    "id": meta.get("id") or fn[:-5],
                    "name": meta.get("name") or fn[:-5],
                    "description": meta.get("description", ""),
                    "groups": [g["name"] for g in data.get("groups", [])],
                })
            except Exception:
                continue
    except Exception:
        pass
    return out


def _load_preset(preset_id: str) -> dict | None:
    """Load a preset file (by id or file name)."""
    for cand in (preset_id, preset_id + ".json"):
        path = os.path.join(PRESETS_DIR, os.path.basename(cand))
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
    return None


def _list_plans() -> list:
    """Restructuring plans (plans/*.json) with short info."""
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
    """Write preset -> config.json (incl. generated node-editor graph).

    Sets casing/language/number_pad/prefixes/translations/groups from the
    preset and rebuilds the `graph` so the preset shows up in the Rules tab
    immediately.
    """
    preset = _load_preset(preset_id)
    if preset is None:
        return {"error": "preset not found: %s" % preset_id}
    cfg = {k: preset.get(k) for k in
           ("casing", "language", "number_pad", "prefixes",
            "translations", "groups") if k in preset}
    cfg["graph"] = graphmod.graph_from_groups(preset.get("groups", []))
    cfg["preset"] = preset.get("meta", {}).get("id") or preset_id
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    return {"ok": True, "applied": cfg.get("preset"), "groups": len(cfg.get("groups", []))}


def _load_cfg():
    data = _read_config_data()
    cfg = cfgmod.load_config(data)
    if cfg.extra_translations:
        translations.add_translations(cfg.extra_translations)
    return cfg, data


def _convention(settings: dict, cfg) -> NamingConvention:
    casing = settings.get("casing") or cfg.convention.style.value
    language = settings["language"] if "language" in settings else cfg.convention.language
    pad = int(settings.get("number_pad", cfg.convention.number_pad))
    return NamingConvention(style=Casing(casing), language=language, number_pad=pad)


def _scope(settings: dict, adapter: SceneAdapter):
    if settings.get("selection"):
        return adapter.selected_guids()
    return None


def _rule_dict(r) -> dict:
    return {
        "name": r.name,
        "categories": sorted(r.match_categories),
        "keywords": sorted(r.match_keywords),
        "aliases": sorted(r.aliases),
        "priority": r.priority,
    }


def handle(payload: dict) -> dict:
    op = payload.get("op")
    settings = payload.get("settings", {})
    doc = c4d.documents.GetActiveDocument()
    if doc is None:
        return {"error": "No active document."}
    cfg, data = _load_cfg()

    if op in ("analyze", "export", "export_csv"):
        adapter = SceneAdapter(doc)
        tree = adapter.build_tree()
        report = SceneAnalyzer(cfg.standard).analyze(tree, file_name=doc.GetDocumentName())
        data_dict = report.to_dict()
        # Project size: the .c4d file on disk (if saved).
        try:
            full = os.path.join(doc.GetDocumentPath() or "", doc.GetDocumentName() or "")
            data_dict["file_size"] = os.path.getsize(full) if os.path.isfile(full) else 0
        except Exception:
            data_dict["file_size"] = 0
        try:
            data_dict["materials"] = adapter.scan_materials()
        except Exception:
            data_dict["materials"] = None
        # Timestamp: when this scene was analyzed (Unix ts + locally readable).
        import time
        now = time.time()
        data_dict["analyzed_ts"] = now
        data_dict["analyzed_at"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        _record_history({
            "file": data_dict.get("file") or "(unsaved)",
            "ts": now,
            "at": data_dict["analyzed_at"],
            "objects": data_dict.get("object_count", 0),
            "compliance": data_dict.get("structure_compliance", 0),
            "polys": data_dict.get("total_polys", 0),
            "size": data_dict.get("file_size", 0),
        })
        written = _write_export(data_dict)
        result = {"ok": True, "report": data_dict, "export_path": written}
        if op == "export_csv":
            csv_res = _write_csv(data_dict)
            result["csv_path"] = csv_res[0] if csv_res else None
            result["csv_rows"] = csv_res[1] if csv_res else 0
        return result

    if op == "history":
        return {"ok": True, "history": list(reversed(_read_history()))}

    if op == "presets":
        return {"ok": True, "presets": _list_presets(),
                "active": data.get("preset")}

    if op == "apply_preset":
        return _apply_preset(payload.get("id", ""))

    if op == "plans":
        return {"ok": True, "plans": _list_plans()}

    if op == "apply_plan":
        plan = payload.get("plan")
        if plan is None and payload.get("id"):
            plan = _load_plan(payload["id"])
        if not plan or "operations" not in plan:
            return {"error": "no valid plan (need {operations:[...]})"}
        adapter = SceneAdapter(doc)
        adapter.build_tree()
        res = adapter.apply_plan(plan["operations"])
        return {"ok": True, **res}

    if op == "focus":
        adapter = SceneAdapter(doc)
        adapter.build_tree()
        ok = adapter.focus(payload.get("guid"))
        return {"ok": ok}

    if op == "delete_material":
        adapter = SceneAdapter(doc)
        deleted = adapter.delete_material(payload.get("name", ""))
        return {"ok": True, "deleted": deleted}

    if op == "delete_unused_materials":
        adapter = SceneAdapter(doc)
        deleted = adapter.delete_unused_materials()
        return {"ok": True, "deleted": deleted}

    if op == "detect":
        tree = SceneAdapter(doc).build_tree()
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
        adapter = SceneAdapter(doc)
        tree = adapter.build_tree()
        conv = _convention(settings, cfg)
        scope = _scope(settings, adapter)
        renames = ops.plan_renames(tree, conv, scope=scope, prefixes=cfg.prefixes)
        diff = [{"guid": r.guid, "old": r.old_name, "new": r.new_name} for r in renames]
        if op == "apply_naming":
            applied = adapter.apply_renames(renames)
            return {"ok": True, "applied": applied, "count": len(renames), "diff": diff}
        return {"ok": True, "count": len(renames), "diff": diff}

    if op in ("plan_structure", "apply_structure"):
        adapter = SceneAdapter(doc)
        tree = adapter.build_tree()
        scope = _scope(settings, adapter)
        safe = bool(settings.get("safe", True))
        tidy = bool(settings.get("tidy", True))
        reparents = ops.plan_reparents(tree, cfg.standard, scope=scope,
                                       safe_only=safe, tidy=tidy)
        report = cfg.standard.evaluate(tree)
        in_scope = [f for f in report.misplaced if scope is None or f.guid in scope]
        skipped = len(in_scope) - len(reparents)
        diff = [{"guid": r.guid, "name": r.name, "from": r.from_group, "to": r.to_group}
                for r in reparents]
        if op == "apply_structure":
            applied = adapter.apply_reparents(reparents)
            return {"ok": True, "applied": applied, "count": len(reparents),
                    "diff": diff, "skipped": skipped}
        return {"ok": True, "count": len(reparents), "diff": diff, "skipped": skipped}

    if op in ("plan_translate", "apply_translate"):
        adapter = SceneAdapter(doc)
        tree = adapter.build_tree()
        scope = _scope(settings, adapter)
        props = translatemod.plan_translations(tree, scope=scope)
        if op == "apply_translate":
            # Apply only the guids accepted by the user.
            accepted = set(payload.get("guids") or [])
            chosen = [p for p in props if p.guid in accepted]
            renames = [ops.RenameOp(guid=p.guid, old_name=p.old, new_name=p.new)
                       for p in chosen]
            applied = adapter.apply_renames(renames)
            return {"ok": True, "applied": applied, "count": len(renames)}
        diff = [{"guid": p.guid, "old": p.old, "new": p.new,
                 "words": p.words} for p in props]
        return {"ok": True, "count": len(props), "diff": diff}

    if op in ("plan_layers", "apply_layers"):
        import collections
        adapter = SceneAdapter(doc)
        tree = adapter.build_tree()
        scope = _scope(settings, adapter)
        layerops = ops.plan_layers(tree, scope=scope)
        by_layer = dict(collections.Counter(o.layer for o in layerops))
        diff = [{"guid": o.guid, "name": o.name, "layer": o.layer} for o in layerops]
        if op == "apply_layers":
            applied = adapter.apply_layers(layerops)
            return {"ok": True, "applied": applied, "count": len(layerops),
                    "diff": diff, "by_layer": by_layer}
        return {"ok": True, "count": len(layerops), "diff": diff, "by_layer": by_layer}

    return {"error": "unknown op: %s" % op}
