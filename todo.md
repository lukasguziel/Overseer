# TODO

## SceneOrga

- Preloader / loading state for the web UI
- [x] Respect Object Manager visibility in the asset listing (eye toggle: hidden
  objects excluded from ALL stats by default, toggle to include them)
- [x] Nicer, styled scrollbars
- [x] Fix translate false-positive detection (bug) — Translate is now a
  standalone tool: pick target language (EN/DE), always shows the detected
  language spread, translate rows individually or all at once. Ambiguous DE
  keys that are also English words (bad/wand/regal…) are only translated with
  other German evidence in the name. Naming pass is decoupled — it no longer
  translates, only casing + numbering.
- [x] Texture analysis
- [x] Texture analysis: handle both absolute and relative paths
- [x] Layer analysis (what is on which layer, whether layers exist, what is NOT
  on any layer, etc.) — read-only "Layer overview" tree in the Layers tab:
  expandable layers with color/flags (render-off/hidden/locked/empty), a "No
  layer" bucket, click an object to focus it in C4D.
- [x] footer oder so wo man meinen namen BAMERUS sieht — thin fixed full-width
  black bar at the very bottom, small letter-spaced white "BAMERUS" signature
- 