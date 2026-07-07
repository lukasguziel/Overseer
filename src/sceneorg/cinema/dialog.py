"""GeDialog UI of the Scene Organizer (c4d-dependent, not tested)."""

from __future__ import annotations

import json
import os

import c4d

from .. import config as cfgmod
from ..core import ops
from ..core.analyzer import SceneAnalyzer
from ..naming import casing as naming
from ..naming import detect, translations
from ..naming.convention import NamingConvention
from .adapter import SceneAdapter

REPORT_PATH = r"C:\Users\lukas\code\cinema4d\scene-organizer\scene_report.json"

# Element IDs
CMB_STYLE = 1001
CMB_LANG = 1002
CMB_PAD = 1003
CHK_SCOPE = 1005
CHK_SAFE = 1006
BTN_DETECT = 1007
BTN_RULES = 1008
BTN_ANALYZE = 1010
BTN_NAME_PREVIEW = 1011
BTN_NAME_APPLY = 1012
BTN_STRUCT_PREVIEW = 1013
BTN_STRUCT_APPLY = 1014
TXT_OUT = 1020

# Format presets for the dropdown (label with example).
_STYLE_ITEMS = [
    (2001, "PascalCase        (LightKey01)",     naming.Casing.PASCAL),
    (2002, "camelCase         (lightKey01)",     naming.Casing.CAMEL),
    (2003, "lower_snake       (light_key_01)",   naming.Casing.LOWER_SNAKE),
    (2004, "UPPER_SNAKE       (LIGHT_KEY_01)",   naming.Casing.UPPER_SNAKE),
    (2005, "kebab-case        (light-key-01)",   naming.Casing.KEBAB),
]
_LANG_ITEMS = [
    (2101, "English", naming.LANG_EN),
    (2102, "German", naming.LANG_DE),
    (2103, "No translation", None),
]
_PAD_ITEMS = [
    (2201, "Numbers: 1  (no padding)", 0),
    (2202, "Numbers: 01 (2-digit)", 2),
    (2203, "Numbers: 001 (3-digit)", 3),
]


class SceneOrganizerDialog(c4d.gui.GeDialog):

    def __init__(self):
        super().__init__()
        self._lines = []
        self.cfg = cfgmod.load_config()
        self.config_source = "(Defaults)"

    # -- Config -----------------------------------------------------------
    def _load_config(self):
        # config.json lives next to the .pyp (one directory above this package)
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base, "config.json")
        if os.path.exists(path):
            try:
                with open(path) as fh:
                    data = json.load(fh)
                self.cfg = cfgmod.load_config(data)
                if self.cfg.extra_translations:
                    translations.add_translations(self.cfg.extra_translations)
                self.config_source = path
            except Exception as e:
                self._log("config.json error (using defaults): %s" % e)
                self.cfg = cfgmod.load_config()

    # -- Layout -----------------------------------------------------------
    def CreateLayout(self):
        self.SetTitle("Scene Organizer")

        self.GroupBegin(3000, c4d.BFH_SCALEFIT, cols=2, rows=0)
        self.GroupBorderSpace(6, 6, 6, 6)
        self.AddStaticText(0, c4d.BFH_LEFT, name="Casing:")
        self.AddComboBox(CMB_STYLE, c4d.BFH_SCALEFIT)
        for cid, label, _ in _STYLE_ITEMS:
            self.AddChild(CMB_STYLE, cid, label)
        self.AddStaticText(0, c4d.BFH_LEFT, name="Language:")
        self.AddComboBox(CMB_LANG, c4d.BFH_SCALEFIT)
        for cid, label, _ in _LANG_ITEMS:
            self.AddChild(CMB_LANG, cid, label)
        self.AddStaticText(0, c4d.BFH_LEFT, name="Numbering:")
        self.AddComboBox(CMB_PAD, c4d.BFH_SCALEFIT)
        for cid, label, _ in _PAD_ITEMS:
            self.AddChild(CMB_PAD, cid, label)
        self.GroupEnd()

        self.GroupBegin(3003, c4d.BFH_SCALEFIT, cols=2, rows=0)
        self.GroupBorderSpace(6, 0, 6, 6)
        self.AddCheckbox(CHK_SCOPE, c4d.BFH_LEFT, 0, 0, name="Selection only")
        self.AddCheckbox(CHK_SAFE, c4d.BFH_LEFT, 0, 0,
                         name="Safety filter (protect generator children)")
        self.GroupEnd()

        self.GroupBegin(3002, c4d.BFH_SCALEFIT, cols=2, rows=0)
        self.GroupBorderSpace(6, 0, 6, 6)
        self.AddButton(BTN_DETECT, c4d.BFH_SCALEFIT, name="Detect format from scene")
        self.AddButton(BTN_RULES, c4d.BFH_SCALEFIT, name="Show active rules")
        self.GroupEnd()

        self.GroupBegin(3001, c4d.BFH_SCALEFIT, cols=3, rows=0)
        self.GroupBorderSpace(6, 0, 6, 6)
        self.AddButton(BTN_ANALYZE, c4d.BFH_SCALEFIT, name="Analyze")
        self.AddButton(BTN_NAME_PREVIEW, c4d.BFH_SCALEFIT, name="Naming preview")
        self.AddButton(BTN_NAME_APPLY, c4d.BFH_SCALEFIT, name="Apply naming")
        self.AddButton(0, c4d.BFH_SCALEFIT, name="")
        self.AddButton(BTN_STRUCT_PREVIEW, c4d.BFH_SCALEFIT, name="Structure preview")
        self.AddButton(BTN_STRUCT_APPLY, c4d.BFH_SCALEFIT, name="Apply structure")
        self.GroupEnd()

        self.AddMultiLineEditText(
            TXT_OUT, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
            initw=560, inith=340,
            style=c4d.DR_MULTILINE_READONLY | c4d.DR_MULTILINE_MONOSPACED,
        )
        return True

    def InitValues(self):
        self._load_config()
        self._set_combo(CMB_STYLE, _STYLE_ITEMS, self.cfg.convention.style)
        self._set_combo(CMB_LANG, _LANG_ITEMS, self.cfg.convention.language)
        self._set_combo(CMB_PAD, _PAD_ITEMS, self.cfg.convention.number_pad)
        self.SetBool(CHK_SCOPE, False)
        self.SetBool(CHK_SAFE, True)
        self._log("Ready. Config: %s" % self.config_source)
        self._log("Tip: 'Analyze' for statistics, 'Show active rules' for the rules.")
        return True

    # -- Output -----------------------------------------------------------
    def _log(self, text):
        self._lines.append(text)
        self.SetString(TXT_OUT, "\n".join(self._lines))

    def _reset(self):
        self._lines = []

    def _convention(self):
        sid = self.GetInt32(CMB_STYLE)
        style = next(s for cid, _, s in _STYLE_ITEMS if cid == sid)
        lid = self.GetInt32(CMB_LANG)
        lang = next(lv for cid, _, lv in _LANG_ITEMS if cid == lid)
        pid = self.GetInt32(CMB_PAD)
        pad = next(p for cid, _, p in _PAD_ITEMS if cid == pid)
        return NamingConvention(style=style, language=lang, number_pad=pad)

    def _set_combo(self, combo_id, items, value):
        for cid, _, val in items:
            if val == value:
                self.SetInt32(combo_id, cid)
                return

    def _scope(self, adapter):
        if self.GetBool(CHK_SCOPE):
            sel = adapter.selected_guids()
            return sel
        return None

    # -- Actions ----------------------------------------------------------
    def Command(self, cid, msg):
        doc = c4d.documents.GetActiveDocument()
        if cid == BTN_DETECT:
            self._do_detect(doc)
        elif cid == BTN_RULES:
            self._do_rules()
        elif cid == BTN_ANALYZE:
            self._do_analyze(doc)
        elif cid == BTN_NAME_PREVIEW:
            self._do_name(doc, apply=False)
        elif cid == BTN_NAME_APPLY:
            self._do_name(doc, apply=True)
        elif cid == BTN_STRUCT_PREVIEW:
            self._do_struct(doc, apply=False)
        elif cid == BTN_STRUCT_APPLY:
            self._do_struct(doc, apply=True)
        return True

    def _do_rules(self):
        self._reset()
        conv = self._convention()
        self._log("=== ACTIVE RULES ===")
        self._log("Config source: %s" % self.config_source)
        self._log("Naming: Casing=%s  Language=%s  Number-Pad=%d" % (
            conv.style.value, conv.language, conv.number_pad))
        if self.cfg.prefixes:
            self._log("Type prefixes: " + ", ".join(
                "%s->%s" % (k, v) for k, v in self.cfg.prefixes.items()))
        else:
            self._log("Type prefixes: (none)")
        self._log("Options: Selection only=%s  Safety filter=%s" % (
            self.GetBool(CHK_SCOPE), self.GetBool(CHK_SAFE)))
        self._log("")
        self._log("Structure groups (priority descending):")
        for r in self.cfg.standard.rules:
            cats = ",".join(sorted(r.match_categories)) or "-"
            kw = ", ".join(sorted(r.match_keywords)) or "-"
            al = ", ".join(sorted(r.aliases)) or "-"
            self._log("  [%d] %s" % (r.priority, r.name))
            self._log("       Categories: %s" % cats)
            self._log("       Keywords:   %s" % kw)
            self._log("       Aliases:    %s" % al)
        self._log("")
        self._log("Example renames:")
        for sample in ["stuhl_01", "KAMERA MAIN", "Wand-Nord", "keyLight 3"]:
            self._log("   %-16s -> %s" % (sample, conv.normalize(sample)))

    def _do_detect(self, doc):
        self._reset()
        tree = SceneAdapter(doc).build_tree()
        names = [n.name for n in tree.walk()]
        result = detect.detect_convention(names)
        self._set_combo(CMB_STYLE, _STYLE_ITEMS, result.style)
        self._set_combo(CMB_LANG, _LANG_ITEMS, result.language)
        self._set_combo(CMB_PAD, _PAD_ITEMS, result.number_pad)
        self._log("=== FORMAT DETECTED ===")
        self._log("Casing distribution:   " + _fmt(result.casing_distribution))
        self._log("Language distribution: " + _fmt(result.language_distribution))
        self._log("-> Suggestion: %s / Language=%s / Number-Pad=%d (confidence %.0f%%)" % (
            result.style.value, result.language, result.number_pad,
            result.confidence * 100))
        if result.confidence < 0.5:
            self._log("Note: low confidence - the scene has no consistent scheme.")
        self._log("Dropdowns set. Adjust if needed, then 'Naming preview'.")

    def _do_analyze(self, doc):
        self._reset()
        adapter = SceneAdapter(doc)
        tree = adapter.build_tree()
        report = SceneAnalyzer(self.cfg.standard).analyze(tree, file_name=doc.GetDocumentName())
        self._log("=== ANALYSIS: %s ===" % report.file)
        self._log("Objects: %d   |   Max depth: %d" % (report.object_count, report.max_depth))
        self._log("Types:       " + _fmt(report.types))
        self._log("Categories:  " + _fmt(report.categories))
        self._log("Casing:      " + _fmt(report.casing))
        self._log("Language:    " + _fmt(report.language))
        self._log("Lights per group:  " + _fmt(report.lights_by_group))
        self._log("Cameras per group: " + _fmt(report.cameras_by_group))
        self._log("Structure compliance: %.0f%%" % (report.structure_compliance * 100))
        if report.misplaced:
            self._log("Misplaced (%d):" % len(report.misplaced))
            for m in report.misplaced[:20]:
                self._log("   %-24s %s -> %s" % (m["name"][:24], m["current"], m["expected"]))
        try:
            with open(REPORT_PATH, "w") as fh:
                json.dump(report.to_dict(), fh, ensure_ascii=True, indent=1)
            self._log("Report: " + REPORT_PATH)
        except Exception as e:
            self._log("Report error: %s" % e)

    def _do_name(self, doc, apply):
        self._reset()
        conv = self._convention()
        adapter = SceneAdapter(doc)
        tree = adapter.build_tree()
        scope = self._scope(adapter)
        renames = ops.plan_renames(tree, conv, scope=scope, prefixes=self.cfg.prefixes)
        self._log("=== NAMING (%s) ===" % ("APPLY" if apply else "Preview"))
        self._log("Scope: %s%s" % (
            "Selection (%d)" % len(scope) if scope is not None else "whole scene",
            "  Prefixes active" if self.cfg.prefixes else ""))
        self._log("%d renames planned:" % len(renames))
        for r in renames[:40]:
            self._log("   %-28s -> %s" % (r.old_name[:28], r.new_name))
        if len(renames) > 40:
            self._log("   ... (+%d more)" % (len(renames) - 40))
        if apply and renames:
            n = adapter.apply_renames(renames)
            self._log("%d objects renamed (undoable)." % n)

    def _do_struct(self, doc, apply):
        self._reset()
        adapter = SceneAdapter(doc)
        tree = adapter.build_tree()
        scope = self._scope(adapter)
        safe = self.GetBool(CHK_SAFE)
        reparents = ops.plan_reparents(tree, self.cfg.standard, scope=scope, safe_only=safe)
        # how many were skipped for safety reasons?
        report = self.cfg.standard.evaluate(tree)
        in_scope = [f for f in report.misplaced if scope is None or f.guid in scope]
        skipped = len(in_scope) - len(reparents)
        self._log("=== STRUCTURE (%s) ===" % ("APPLY" if apply else "Preview"))
        self._log("Scope: %s   Safety filter: %s" % (
            "Selection (%d)" % len(scope) if scope is not None else "whole scene", safe))
        self._log("%d regroupings planned:" % len(reparents))
        for r in reparents[:40]:
            self._log("   %-24s %s -> %s" % (r.name[:24], r.from_group, r.to_group))
        if len(reparents) > 40:
            self._log("   ... (+%d more)" % (len(reparents) - 40))
        if skipped > 0:
            self._log("%d misplaced protected by safety filter (not moved)." % skipped)
        if apply and reparents:
            n = adapter.apply_reparents(reparents)
            self._log("%d objects regrouped (undoable)." % n)


def _fmt(d):
    return ", ".join("%s(%d)" % (k, v) for k, v in sorted(d.items(), key=lambda x: -x[1]))
