// The in-app documentation, one entry per AREA — opened by the little "i"
// sitting in that area's SectionIntro (components/InfoButton.tsx). Content
// mirrors docs/FEATURES.md, scoped to the area the intro opens: what it
// shows, what every control does, and the one thing worth knowing that the
// UI can't say inline. An area with several boxes explains them as groups.
// Keep each feature to one sentence; the modal is a guide, not a manual.

export interface DocFeature { name: string; desc: string }

export interface SectionDoc {
  title: string                 // the area's name, as printed in its intro
  tagline: string               // one line: what this area is FOR
  features?: DocFeature[]       // flat list (single-box areas)
  groups?: { head: string; features: DocFeature[] }[]  // one group per box
  tip?: string                  // optional closing advice (workflow, gotcha)
}

export const SECTION_DOCS: Record<string, SectionDoc> = {

  // ---- Overview (tab-level) -------------------------------------------------

  'overview': {
    title: 'Overview',
    tagline: 'Your scene’s dashboard: how big, how healthy, and where to start.',
    groups: [
      { head: 'Key tiles & health', features: [
        { name: 'Tiles with trends', desc: 'Objects, polygons and project size with sparkline and delta from your analysis history.' },
        { name: 'Health score & sub-rings', desc: 'Naming, translate, layers, materials, tags and files each get a percentage; rings jump to their tab, the navigation carries the same progress as an underline.' },
        { name: 'Total footprint', desc: 'Project file + textures on disk + external files summed into the number you’d actually hand off.' },
      ]},
      { head: 'Geometry map', features: [
        { name: 'Treemap by polygons', desc: 'Every object sized by polygon count, tinted by category; click a tile to select & frame it in the viewport.' },
      ]},
      { head: 'Texture map', features: [
        { name: 'Area = pixels', desc: 'Maps sized by width × height — the VRAM factor, regardless of JPG size on disk; colour = resolution tier (deep red = 8K).' },
        { name: 'Click to focus', desc: 'A click selects the material and frames the first object using it.' },
      ]},
      { head: 'Naming consistency', features: [
        { name: 'Casing & language mix', desc: 'Convention-aware casing distribution plus detected source languages, taken verbatim from the Translate engine.' },
      ]},
      { head: 'Materials & textures', features: [
        { name: 'Summary numbers', desc: 'Totals, unused materials, missing textures, disk footprint and absolute paths — managed on the Materials tab.' },
      ]},
      { head: 'Polygon concentration', features: [
        { name: 'Where the weight lives', desc: 'Top-10 share, objects covering 80%, and heavy outliers (>5% of the scene), clickable.' },
      ]},
      { head: 'Texture budget', features: [
        { name: 'Estimated VRAM', desc: 'width × height × 4 bytes per map incl. mipmaps (~1.33×) — plus the resolution mix and the heaviest maps.' },
      ]},
    ],
    tip: 'A 100% ring means “every item decided”, not “everything changed” — accepted-as-is counts as done.',
  },

  // ---- Naming ---------------------------------------------------------------

  'naming-preview': {
    title: 'Rename rules',
    tagline: 'Every rename your convention would cause — old → new, nothing applied until you say so.',
    features: [
      { name: 'Settings on the left', desc: 'Casing style (with keep-separators / keep-specials), number padding and duplicate handling — the preview follows live.' },
      { name: 'Rule tags', desc: 'Each row names the rule that fired: casing, numbering, prefix or unique.' },
      { name: 'Per-row decide', desc: 'Green ✓ applies that one rename (undoable), the grey ✓ accepts the current name as-is; click the row to select & frame the object first.' },
      { name: 'Batch pair', desc: '“Apply all” renames the whole list in one undo step; “Keep all as-is” accepts everything without touching the scene.' },
      { name: 'Hidden objects', desc: 'The eye toggle decides whether hidden objects are part of the worklist; they always keep blocking duplicate names.' },
    ],
    tip: 'Accepted names are remembered in the config and stop counting as todos — restore them any time in “Accepted as-is” below.',
  },
  'naming-cleanup': {
    title: 'Name cleanup',
    tagline: 'Names no rule can fix automatically — they need a human word.',
    features: [
      { name: 'Default names', desc: 'Objects still called “Cube”, “Null”, “Light” … say nothing about what they are; ✎ renames them inline.' },
      { name: 'Duplicate names', desc: 'The same name used by several objects (×n shows how many) — rename individually, or let “Make duplicates unique” number them.' },
      { name: 'Accept per row', desc: 'The grey ✓ accepts a name as fine; “Keep all as-is” clears the whole bucket.' },
      { name: 'Click to focus', desc: 'Any item selects & frames its object in the viewport.' },
    ],
  },

  // ---- Translate (tab-level) --------------------------------------------------

  'translate': {
    title: 'Translate',
    tagline: 'Names rewritten into the target language, word by word — casing, separators and numbers survive.',
    features: [
      { name: 'Two engines', desc: 'Google translates any language online (words are sent to Google); Offline uses bundled dictionaries and never leaves the machine.' },
      { name: 'Word-level diff', desc: 'Each row shows exactly which words change; the tooltip carries the full word mapping.' },
      { name: 'Source-language tag', desc: 'Every proposal is tagged with the language it was detected as.' },
      { name: 'Per-row decide', desc: 'Apply one translation, or accept the original name as-is — same gestures as everywhere.' },
      { name: 'Detected-in-scene panel', desc: 'A name counts under its source language only while translating would change it — applied scenes converge on the target language.' },
    ],
  },

  // ---- Layers (tab-level) -------------------------------------------------------

  'layers': {
    title: 'Layers',
    tagline: 'Every object that should live on a layer gets one — without moving a single object.',
    groups: [
      { head: 'Layer overview', features: [
        { name: 'Layer tree', desc: 'Colour swatch, object / material / tag counts, polygon count and the V/R/L flags per layer, expandable to the member objects.' },
        { name: 'Empty-layer cleanup', desc: 'Layers nothing references can be deleted per row or all at once (one undo step) — or accepted and kept.' },
        { name: 'Colour gradient', desc: 'Spread a two-colour gradient across the layers in overview order.' },
      ]},
      { head: 'No layer', features: [
        { name: 'Inline picker', desc: '✓ opens the layer picker on the row: existing layers autocomplete, a new name creates the layer on assign.' },
        { name: 'Suggested layers', desc: 'Objects whose ancestors sit on a layer get that layer proposed; “Assign suggested” applies all suggestions in one confirmed step.' },
        { name: 'Batch assign', desc: 'Type one layer name and give it to the whole list in a single undoable step.' },
        { name: 'Fine without', desc: 'The grey ✓ accepts “no layer” for that object; it stops counting as a todo.' },
      ]},
      { head: 'Layer assignment preview', features: [
        { name: 'Scheme-based plan', desc: 'Cameras, lights and other categories map to their standard layers; your rule set can add its own layer rules.' },
        { name: 'Idempotent', desc: 'Objects already on their target layer never reappear in the list.' },
      ]},
      { head: 'Mixed-layer hierarchies', features: [
        { name: 'Informational only', desc: 'Objects on a different layer than their parent — often intentional, never changed automatically; accept a mix to hide it.' },
      ]},
    ],
    tip: 'Layers are orthogonal to your null structure — this tab never moves an object.',
  },

  // ---- Materials --------------------------------------------------------------

  'materials': {
    title: 'Materials',
    tagline: 'Materials and the textures behind them — the invisible half of a scene’s size.',
    groups: [
      { head: 'Unused materials', features: [
        { name: 'Scope-aware', desc: '“Visible only” lists materials used nowhere; “All objects” adds those used exclusively by hidden objects, badged separately.' },
        { name: 'Preview thumbnails', desc: 'Each row renders the material’s real preview sphere; a click selects it in the Material Manager.' },
        { name: 'Delete or keep', desc: 'Delete per row or all deletable ones at once (confirmed, undoable) — or accept keepers so they stop counting.' },
      ]},
      { head: 'Textures', features: [
        { name: 'One paths workbench', desc: 'Every map filtered by path status and resolution tier — details under the “Textures” heading below.' },
      ]},
    ],
    tip: 'Anything a visible object uses never shows up as unused — the list is safe by construction.',
  },
  'mat-textures': {
    title: 'Textures',
    tagline: 'Every image map the scene references: paths, resolutions, problems — and the fixes.',
    features: [
      { name: 'Filters', desc: 'Narrow by path status (absolute / relative / missing) and resolution tier; each row carries its badges.' },
      { name: 'Missing maps, per row', desc: 'Pick a replacement in C4D’s file dialog, clear the dead reference, or accept it as missing — works across Octane/Redshift node setups.' },
      { name: 'Missing maps, in batch', desc: 'Relink everything from a search folder (filename match, project-relative when possible) or clear all dead references.' },
      { name: 'Shrink', desc: 'Downscale a map to 50/25/12.5% — a resized copy is written next to the original and the material relinked to it.' },
      { name: 'Path fixes', desc: 'Rewrite absolute in-project paths to relative per row or in bulk; collect out-of-project files into tex/ and relink.' },
      { name: 'Thumbnails', desc: 'Hover shows channel/bit-depth/colorspace specs; clicking the thumbnail opens the image in your picture viewer.' },
    ],
  },

  // ---- Tags (tab-level) ------------------------------------------------------------

  'tags': {
    title: 'Tags',
    tagline: 'Every tag in the scene, audited — the fastest way to catch shading-setup drift.',
    groups: [
      { head: 'Missing phong tags', features: [
        { name: 'Faceted by accident', desc: 'Polygon objects without a Phong tag render hard-faceted; add one per row or all at once, at the scene’s dominant angle.' },
        { name: 'Or a look', desc: 'Flat shading can be intentional — accept objects that should stay faceted.' },
      ]},
      { head: 'Duplicate material tags', features: [
        { name: 'Pure clutter', desc: 'The same material assigned twice on one object — delete the redundant copies per row or in batch, the first stays.' },
      ]},
      { head: 'Phong angles', features: [
        { name: 'Distribution', desc: 'How many tags sit at which angle (84× 20°, 981× 40° …), the dominant one marked.' },
        { name: 'Set uniform angle', desc: 'Give every phong tag the same angle in one undoable step — presets or a custom value.' },
      ]},
      { head: 'All tag types', features: [
        { name: 'Full inventory', desc: 'Every tag type with count, expandable to the carrying objects, and “Select in C4D” per type.' },
        { name: 'Data tags filtered', desc: 'Invisible per-geometry data tags are hidden so the real tags stay readable; selection tags fold into one row.' },
      ]},
    ],
  },

  // ---- Files (tab-level) --------------------------------------------------------------

  'files': {
    title: 'Files',
    tagline: 'Every non-image file the scene references — Alembic, caches, IES, audio, video.',
    groups: [
      { head: 'Missing files', features: [
        { name: 'Per row', desc: 'Pick the replacement in C4D’s file dialog, or accept the file as missing (it stops counting against the score).' },
        { name: 'Relink from folder', desc: 'Point at a search folder — every missing name found there is relinked, project-relative when possible.' },
        { name: 'Select owners', desc: 'Select all objects referencing missing files in C4D at once.' },
      ]},
      { head: 'Referenced files', features: [
        { name: 'Kind filter', desc: 'Chips per kind (Alembic, cache, IES …) with counts; the list sorts by size.' },
        { name: 'Make relative', desc: 'Absolute paths under the project folder are rewritten to relative in one undoable step.' },
        { name: 'Click to focus', desc: 'Each row selects & frames the referencing object.' },
      ]},
    ],
    tip: 'Image textures live on the Materials tab — this list is everything else.',
  },

  // ---- Assets (tab-level) ---------------------------------------------------------------

  'assets': {
    title: 'Assets',
    tagline: 'A searchable, sortable inventory of every object — and a batch tool, not just a list.',
    features: [
      { name: 'Search & facets', desc: 'Filter by name/type/layer text, category chips, per-type facets, “only geometry” and “no layer” toggles.' },
      { name: 'Sortable columns', desc: 'Polygons, points, children, name, layer — find the heaviest objects instantly.' },
      { name: 'Batch actions', desc: 'Check rows, then assign them to a layer or move them into a group — targets autocomplete, are created if missing, one undo step.' },
      { name: 'Click to focus', desc: 'Any row selects & frames the object in the viewport.' },
      { name: 'Hidden-object aware', desc: 'Objects hidden in the Object Manager are marked and can be excluded from all stats.' },
    ],
  },

  // ---- Generators (tab-level) -------------------------------------------------------------

  'generators': {
    title: 'Generators',
    tagline: 'Same generator type, different settings? Every disagreement, one card per type.',
    groups: [
      { head: 'Settings audit', features: [
        { name: 'Mixed settings only', desc: 'Settings everyone agrees on collapse into one quiet line — only real spread gets a block.' },
        { name: 'Value chips', desc: 'Current values as value × count chips, the dominant one tagged MOST; clicking a chip selects those objects.' },
        { name: 'Change all to …', desc: 'Align every object of a type on one value in a single undoable step, or fix the differing ones per row.' },
        { name: 'Audited types', desc: 'Subdivision Surface, Cloner, Extrude, Instance and Symmetry, with C4D’s own value labels and icons.' },
      ]},
      { head: 'Viewport cost', features: [
        { name: 'Real rebuild timing', desc: 'Each candidate’s cache is dirtied and the document pass timed; the idle cost is subtracted, the fastest of several runs counts.' },
        { name: 'On demand only', desc: 'Measuring costs time on heavy scenes, so it only runs when you click it — never in the background.' },
      ]},
    ],
    tip: 'On/off states are deliberately not audited — enabling a generator is a per-shot artistic choice, not a finding.',
  },

  // ---- Sims (tab-level) -----------------------------------------------------------------

  'sims': {
    title: 'Sims',
    tagline: 'Simulation setups that cost you silently — found and fixable.',
    groups: [
      { head: 'Findings', features: [
        { name: 'Active on hidden', desc: 'Enabled sims on hidden geometry burn solve time you never see; disable per row or all at once.' },
        { name: 'Unbaked sims', desc: 'Live simulations without a cache, flagged before you hand the scene off.' },
        { name: 'Disabled leftovers', desc: 'Dead sim tags listed as cleanup candidates — deleting stays your call.' },
      ]},
      { head: 'All simulation participants', features: [
        { name: 'Full roster', desc: 'Cloth, dynamics, colliders, pyro, particles, hair — with enabled / cached / hidden badges and per-kind select-in-C4D.' },
      ]},
    ],
  },

  // ---- Misc (tab-level) & shared panels ----------------------------------------------------

  'misc': {
    title: 'Misc',
    tagline: 'History and plumbing — what makes the rest of the tool trustworthy.',
    groups: [
      { head: 'Change history', features: [
        { name: 'One entry per run', desc: 'Every tool action logged with before → after per object; expand an entry to read every single op.' },
        { name: 'Revert', desc: 'Restore a whole run or a single op — the revert itself is one undo step and is marked in the log.' },
        { name: 'Travels with the scene', desc: 'The journal is stored inside the .c4d document (plus a sidecar file), so it survives on other machines.' },
      ]},
      { head: 'Analysis history', features: [
        { name: 'Snapshots per project', desc: 'Objects, polygons, file size and compliance per run (up to 100) — the data behind the Overview trends.' },
      ]},
      { head: 'Read the scene on your phone', features: [
        { name: 'Opt-in LAN access', desc: 'A QR code opens this UI on your phone; off by default, the bind changes on a C4D restart.' },
      ]},
    ],
    tip: 'Turn phone access off again when you’re done — while enabled, anyone on your network can reach the tool.',
  },
  'accepted': {
    title: 'Accepted as-is',
    tagline: 'Every “this is fine” decision you made, across all areas — restorable any time.',
    features: [
      { name: 'One pile, grouped', desc: 'Accepted names, layers, materials, textures and files, grouped by the area they came from; each tab shows only what it can act on.' },
      { name: 'Not a todo', desc: 'Accepted items are remembered in the config and never counted against the health scores.' },
      { name: 'Restore', desc: 'Per item or per group — restored items become todos again immediately.' },
    ],
  },
  'area-history': {
    title: 'History',
    tagline: 'What the tool changed in this area, newest first — revert right here.',
    features: [
      { name: 'This area only', desc: 'Only the runs that touched this area; the full cross-area log lives on the Misc tab.' },
      { name: 'Revert per run or op', desc: 'Expand an entry to revert single ops, or revert the whole run in one undo step.' },
      { name: 'Mixed runs reduced', desc: 'A one-click (apply-all) run shows only this area’s ops here — reverting it here reverts exactly those.' },
    ],
  },
}
