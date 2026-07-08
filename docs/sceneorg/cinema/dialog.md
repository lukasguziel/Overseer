# cinema/dialog.py

GeDialog UI of the Scene Organizer (c4d-dependent, not tested). Native C4D
dialog that drives the same pure `sceneorg` logic as the web frontend. UI copy
is a mix of English labels; string literals are user-facing and must stay
verbatim.

## Constants

- `REPORT_PATH` — absolute path where `Analyze` writes `scene_report.json`
  (the channel Claude reads).
- Element ids (`CMB_*`, `CHK_*`, `BTN_*`, `TXT_OUT`) — GeDialog gadget ids.
- `_STYLE_ITEMS` / `_LANG_ITEMS` / `_PAD_ITEMS` — (id, label, value) tuples that
  back the casing / language / numbering dropdowns; labels include an example.

## SceneOrganizerDialog(c4d.gui.GeDialog)

- `__init__` — loads default config, sets `config_source` to "(Defaults)".
- `_load_config()` — reads `config.json` next to the .pyp (one dir above this
  package); on success registers any `extra_translations`; falls back to defaults
  and logs on error.
- `CreateLayout()` — builds the dialog: casing/language/numbering combos, the
  "Selection only" and "Safety filter" checkboxes, Detect/Rules buttons, the
  Analyze / Naming preview / Apply naming / Structure preview / Apply structure
  button grid, and a read-only monospaced multiline output.
- `InitValues()` — loads config, syncs combos to the active convention, defaults
  scope off / safety on, prints ready + tip lines.
- `_log(text)` / `_reset()` — append to and clear the output buffer.
- `_convention()` — builds a `NamingConvention` from the current combo
  selections.
- `_set_combo(combo_id, items, value)` — selects the combo entry whose value
  matches.
- `_scope(adapter)` — returns selected guids when "Selection only" is checked,
  else None (whole scene).
- `Command(cid, msg)` — dispatches button clicks to the `_do_*` handlers using
  the active document.
- `_do_rules()` — prints the active naming convention, type prefixes, options,
  structure group rules (priority/categories/keywords/aliases), and example
  renames.
- `_do_detect(doc)` — detects the scheme from scene names, sets the combos to the
  suggestion, and prints casing/language distributions and confidence (warns when
  confidence < 0.5).
- `_do_analyze(doc)` — runs `SceneAnalyzer`, prints stats (types/categories/
  casing/language, lights & cameras per group, compliance, misplaced list) and
  writes `scene_report.json` to `REPORT_PATH`.
- `_do_name(doc, apply)` — plans renames for the current scope+prefixes, prints a
  capped diff; when `apply`, calls `apply_renames` (undoable) and reports the
  count.
- `_do_struct(doc, apply)` — plans reparents honoring scope and the safety filter,
  reports how many misplaced objects were protected/skipped; when `apply`, calls
  `apply_reparents` (undoable).

## Module functions

- `_fmt(d)` — formats a count dict as `key(n)` pairs sorted by descending count.
