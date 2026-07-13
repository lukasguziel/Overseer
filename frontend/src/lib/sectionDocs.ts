// The in-app documentation, one entry per SECTION (card / workbench) — shown
// by the little "i" in that section's bottom-left corner (components/
// InfoButton.tsx). Content mirrors docs/FEATURES.md, but scoped to exactly
// the area the artist is looking at: what the section shows, what every
// control in it does, and the one thing worth knowing that the UI can't say
// inline. Keep each feature to one sentence; the modal is a guide, not a manual.

export interface SectionDoc {
  title: string                 // the section's own name, as printed in its head
  tagline: string               // one line: what this area is FOR
  features: { name: string; desc: string }[]
  tip?: string                  // optional closing advice (workflow, gotcha)
}

export const SECTION_DOCS: Record<string, SectionDoc> = {

  // ---- Overview -----------------------------------------------------------

  'ov-workflow': {
    title: 'Cleanup workflow',
    tagline: 'Your scene’s health at a glance — and the suggested order to work in.',
    features: [
      { name: 'Health score & sub-rings', desc: 'Naming, translate, layers, materials, tags and files each get a percentage; the overall score is their average.' },
      { name: 'Rings jump to their tab', desc: 'Click any ring to open the matching tab; the navigation carries the same progress as an underline.' },
      { name: 'Left to right', desc: 'The steps are ordered so early wins (naming, layers) make the later areas easier to read.' },
      { name: 'Live counts', desc: 'Every ring counts the same todos its tab shows — apply or accept items there and the ring closes.' },
    ],
    tip: 'A 100% ring means “every item decided”, not “everything changed” — accepted-as-is counts as done.',
  },
  'ov-geomap': {
    title: 'Geometry map',
    tagline: 'Every object sized by its polygon count — the heaviest assets stand out immediately.',
    features: [
      { name: 'Treemap by polygons', desc: 'Tile area = polygon count; labels appear where they fit.' },
      { name: 'Click to focus', desc: 'A click selects & frames that object in the Cinema 4D viewport.' },
      { name: 'Category colours', desc: 'Tiles are tinted by category (mesh, light, camera …) so clusters read at a glance.' },
    ],
  },
  'ov-texmap': {
    title: 'Texture map',
    tagline: 'Every referenced image sized by its pixel count — the real VRAM factor, not the file size.',
    features: [
      { name: 'Area = width × height', desc: 'A 30 MB JPG can be harmless and a 4 MB PNG enormous — pixels are what the GPU pays for.' },
      { name: 'Heat by resolution tier', desc: 'Deep red = 8K, fading towards grey below 1K.' },
      { name: 'Click to focus', desc: 'A click selects the material and frames the first object using it.' },
    ],
  },
  'ov-naming': {
    title: 'Naming consistency',
    tagline: 'How uniform your object names are — casing styles and language mix.',
    features: [
      { name: 'Casing distribution', desc: 'Share of PascalCase / lower_snake / mixed … across all names, convention-aware.' },
      { name: 'Language mix', desc: 'Detected source languages, taken verbatim from the Translate engine — a name only counts while translating would change it.' },
    ],
    tip: 'The Naming and Translate tabs are the tools that move these bars.',
  },
  'ov-materials': {
    title: 'Materials & textures',
    tagline: 'The invisible half of the scene’s size, summarised.',
    features: [
      { name: 'Material counts', desc: 'Total materials, how many are unused, and missing texture references.' },
      { name: 'Disk & VRAM totals', desc: 'Texture bytes on disk plus the estimated uncompressed RAM/VRAM cost.' },
    ],
  },
  'ov-polys': {
    title: 'Polygon concentration',
    tagline: 'Which top-level groups hold the geometry.',
    features: [
      { name: 'Polygons by group', desc: 'The heaviest top-level containers, so you know where the weight lives before optimising.' },
      { name: 'Top-10 share', desc: 'How much of the whole scene the ten heaviest objects account for.' },
    ],
  },
  'ov-budget': {
    title: 'Texture budget',
    tagline: 'What your maps cost uncompressed — resolution mix and the heaviest offenders.',
    features: [
      { name: 'Resolution mix', desc: 'How many 8K / 4K / 2K / smaller maps the scene references.' },
      { name: 'Estimated VRAM', desc: 'width × height × 4 bytes per map including mipmaps (~1.33×) — independent of the compressed file size.' },
      { name: 'Heaviest maps, clickable', desc: 'The top entries select their material in Cinema 4D; shrinking lives on the Materials tab.' },
    ],
  },

  // ---- Naming ---------------------------------------------------------------

  'naming-preview': {
    title: 'Rename preview',
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

  // ---- Translate ------------------------------------------------------------

  'translate-preview': {
    title: 'Translation preview',
    tagline: 'Names rewritten into the target language, word by word — casing, separators and numbers survive.',
    features: [
      { name: 'Two engines', desc: 'Google translates any language online (words are sent to Google); Offline uses bundled dictionaries and never leaves the machine.' },
      { name: 'Word-level diff', desc: 'Each row shows exactly which words change; the tooltip carries the full word mapping.' },
      { name: 'Source-language tag', desc: 'Every proposal is tagged with the language it was detected as.' },
      { name: 'Per-row decide', desc: 'Apply one translation, or accept the original name as-is — same gestures as everywhere.' },
      { name: 'Detected-in-scene panel', desc: 'A name counts under its source language only while translating would change it — applied scenes converge on the target language.' },
    ],
  },

  // ---- Layers -----------------------------------------------------------------

  'layers-overview': {
    title: 'Layer overview',
    tagline: 'Every layer in the document: colour, usage, flags — and cleanup for the dead ones.',
    features: [
      { name: 'Layer tree', desc: 'Colour swatch, object / material / tag counts, polygon count and the V/R/L flags per layer, expandable to the member objects.' },
      { name: 'Empty-layer cleanup', desc: 'Layers nothing references can be deleted per row or all at once (one undo step) — or accepted and kept.' },
      { name: 'Colour gradient', desc: 'Tick layers (or none for all) and spread a two-colour gradient across them in overview order.' },
      { name: 'Click to focus', desc: 'A layer row selects its objects; object rows frame them in the viewport.' },
    ],
  },
  'layers-nolayer': {
    title: 'No layer',
    tagline: 'Every object without a layer — give it one, or decide it’s fine without.',
    features: [
      { name: 'Inline picker', desc: '✓ opens the layer picker on the row: existing layers autocomplete, a new name creates the layer on assign.' },
      { name: 'Suggested layers', desc: 'Objects whose ancestors sit on a layer get that layer proposed; “Assign suggested” applies all suggestions in one confirmed step.' },
      { name: 'Batch assign', desc: 'Type one layer name and give it to the whole list in a single undoable step.' },
      { name: 'Fine without', desc: 'The grey ✓ accepts “no layer” for that object; it stops counting as a todo.' },
      { name: 'Hierarchy untouched', desc: 'Layers are orthogonal to your null structure — this tool never moves an object.' },
    ],
  },
  'layers-assign': {
    title: 'Layer assignment preview',
    tagline: 'The rule-driven layer plan: which object would land on which layer.',
    features: [
      { name: 'Scheme-based', desc: 'Cameras, lights and other categories map to their standard layers; your rule set can add its own layer rules.' },
      { name: 'Per-row decide', desc: 'Apply single assignments, accept objects as-is, or apply the whole plan in one undo step.' },
      { name: 'Idempotent', desc: 'Objects already on their target layer never reappear in the list.' },
    ],
  },
  'layers-mismatch': {
    title: 'Mixed-layer hierarchies',
    tagline: 'Objects sitting on a different layer than their parent — often intentional, never auto-changed.',
    features: [
      { name: 'Informational only', desc: 'Nothing here is ever changed automatically; the list is a reading aid.' },
      { name: 'Accept per row', desc: 'The ✓ marks a mix as intentional and hides it from the list (restore below).' },
      { name: 'Click to focus', desc: 'Each row selects & frames the object so you can judge the mix in context.' },
    ],
  },

  // ---- Materials --------------------------------------------------------------

  'mat-unused': {
    title: 'Unused materials',
    tagline: 'Materials no object references — the classic leftovers of iteration.',
    features: [
      { name: 'Scope-aware', desc: '“Visible only” lists materials used nowhere; “All objects” adds those used exclusively by hidden objects, badged separately.' },
      { name: 'Preview thumbnails', desc: 'Each row renders the material’s real preview sphere.' },
      { name: 'Delete or keep', desc: 'Delete per row or all deletable ones at once (confirmed, undoable) — or accept keepers so they stop counting.' },
      { name: 'Click to focus', desc: 'A row selects the material in Cinema 4D’s Material Manager.' },
    ],
    tip: 'Anything a visible object uses never shows up here — the list is safe by construction.',
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

  // ---- Tags ---------------------------------------------------------------------

  'tags-overview': {
    title: 'Tags',
    tagline: 'Every tag in the scene, audited — the quickest way to catch shading-setup drift.',
    features: [
      { name: 'Totals', desc: 'Tag count and distinct types across the whole scene.' },
      { name: 'Findings', desc: 'Missing phong tags and duplicate material tags — both count against the Tags health score.' },
    ],
    tip: 'The findings below are fixable in batch; the full inventory sits at the bottom of the tab.',
  },
  'tags-phong': {
    title: 'Missing phong tags',
    tagline: 'Polygon objects without a Phong tag render faceted — usually an accident.',
    features: [
      { name: 'Add per row or all', desc: 'New tags are created at the scene’s dominant angle, in one undo step.' },
      { name: 'Accept as-is', desc: 'Flat shading can be a look — accept objects that should stay faceted.' },
      { name: 'Click to focus', desc: 'Rows select & frame the object.' },
    ],
  },
  'tags-dupes': {
    title: 'Duplicate material tags',
    tagline: 'The same material assigned twice on one object — pure clutter.',
    features: [
      { name: 'Delete duplicates', desc: 'Removes the redundant copies per row or all at once; the first tag always stays.' },
      { name: 'Selection-aware', desc: 'Only true duplicates (same material, same restriction) count — different selections are legitimate.' },
    ],
  },
  'tags-angles': {
    title: 'Phong angles',
    tagline: 'The phong-angle spread across the scene — and one click to unify it.',
    features: [
      { name: 'Distribution', desc: 'How many tags sit at which angle (84× 20°, 981× 40° …).' },
      { name: 'Set uniform angle', desc: 'Give every phong tag the same angle in one undoable step.' },
    ],
    tip: 'Angles are stored in radians in C4D — the tool converts, you think in degrees.',
  },
  'tags-inventory': {
    title: 'All tag types',
    tagline: 'The full tag inventory — every type, every carrier.',
    features: [
      { name: 'Counts per type', desc: 'Every tag type in the scene with its count, expandable to the objects carrying it.' },
      { name: 'Select in C4D', desc: 'Per type: select all carriers in the Object Manager.' },
      { name: 'Data tags filtered', desc: 'Invisible per-geometry data tags (point/polygon/tangent …) are hidden so the real tags stay readable; selection tags are folded into one row.' },
    ],
  },

  // ---- Files ----------------------------------------------------------------------

  'files-missing': {
    title: 'Missing files',
    tagline: 'External references whose file is gone — Alembic, caches, IES, audio, video.',
    features: [
      { name: 'Per row', desc: 'Pick the replacement in C4D’s file dialog, or accept the file as missing (it stops counting against the score).' },
      { name: 'Relink from folder', desc: 'Point at a search folder — every missing name found there is relinked, project-relative when possible.' },
      { name: 'Select owners', desc: 'Select all objects referencing missing files in C4D at once.' },
    ],
  },
  'files-all': {
    title: 'Referenced files',
    tagline: 'Every non-image file the scene points at, with sizes and kinds.',
    features: [
      { name: 'Kind filter', desc: 'Chips per kind (Alembic, cache, IES …) with counts; the list sorts by size.' },
      { name: 'Make relative', desc: 'Absolute paths under the project folder are rewritten to relative in one undoable step.' },
      { name: 'Click to focus', desc: 'Each row selects & frames the referencing object.' },
    ],
    tip: 'Image textures live on the Materials tab — this list is everything else.',
  },

  // ---- Assets ---------------------------------------------------------------------

  'assets': {
    title: 'Objects',
    tagline: 'A searchable, sortable inventory of every object — and a batch tool, not just a list.',
    features: [
      { name: 'Search & facets', desc: 'Filter by name/type/layer text, category chips, per-type facets, “only geometry” and “no layer” toggles.' },
      { name: 'Sortable columns', desc: 'Polygons, points, children, name, layer — find the heaviest objects instantly.' },
      { name: 'Batch actions', desc: 'Check rows, then assign them to a layer or move them into a group — targets autocomplete, are created if missing, one undo step.' },
      { name: 'Click to focus', desc: 'Any row selects & frames the object in the viewport.' },
      { name: 'Hidden-object aware', desc: 'Objects hidden in the Object Manager are marked and can be excluded from all stats.' },
    ],
  },

  // ---- Generators -------------------------------------------------------------------

  'gens-settings': {
    title: 'Generators',
    tagline: 'Same generator type, different settings? Every disagreement, one card per type.',
    features: [
      { name: 'Mixed settings only', desc: 'Settings everyone agrees on collapse into one quiet line — only real spread gets a block.' },
      { name: 'Value chips', desc: 'Current values as value × count chips, the dominant one tagged MOST; clicking a chip selects those objects.' },
      { name: 'Change all to …', desc: 'Align every object of a type on one value in a single undoable step, or fix the differing ones per row.' },
      { name: 'Audited types', desc: 'Subdivision Surface, Cloner, Extrude, Instance and Symmetry, with C4D’s own value labels and icons.' },
    ],
    tip: 'On/off states are deliberately not audited — enabling a generator is a per-shot artistic choice, not a finding.',
  },
  'gens-perf': {
    title: 'Viewport cost',
    tagline: 'Which generator or deformer actually stalls your viewport — measured, not guessed.',
    features: [
      { name: 'Real rebuild timing', desc: 'Each candidate’s cache is dirtied and the document pass timed; the idle cost is subtracted, the fastest of several runs counts.' },
      { name: 'Ranked verdict', desc: 'The slowest rebuilds top the list with a plain-language rating.' },
      { name: 'On demand only', desc: 'Measuring costs time on heavy scenes, so it only runs when you click it — never in the background.' },
    ],
  },

  // ---- Sims -----------------------------------------------------------------------

  'sims-findings': {
    title: 'Simulations',
    tagline: 'Simulation setups that cost you silently — found and fixable.',
    features: [
      { name: 'Active on hidden', desc: 'Enabled sims on hidden geometry burn solve time you never see; disable per row or all at once.' },
      { name: 'Unbaked sims', desc: 'Live simulations without a cache, flagged before you hand the scene off.' },
      { name: 'Disabled leftovers', desc: 'Dead sim tags listed as cleanup candidates — deleting stays your call.' },
    ],
  },
  'sims-all': {
    title: 'All simulation participants',
    tagline: 'The full roster: everything in the scene that simulates or collides.',
    features: [
      { name: 'Every participant', desc: 'Cloth, dynamics, colliders, pyro, particles, hair — with enabled / cached / hidden badges.' },
      { name: 'Select per kind', desc: 'Select all participants of a kind in C4D with one click.' },
    ],
  },

  // ---- Misc & shared panels ----------------------------------------------------------

  'misc-changes': {
    title: 'Change history',
    tagline: 'Every change the tool made, with before → after per object — and revert.',
    features: [
      { name: 'One entry per run', desc: 'Each apply is logged as one entry; expand it to read every single op.' },
      { name: 'Revert', desc: 'Restore a whole run or a single op — the revert itself is one undo step and is marked in the log.' },
      { name: 'Travels with the scene', desc: 'The journal is stored inside the .c4d document (plus a sidecar file), so it survives on other machines.' },
      { name: 'Cross-area', desc: 'This is the full log; every work tab shows its own slice at its foot.' },
    ],
  },
  'misc-analysis': {
    title: 'Analysis history',
    tagline: 'Every analysis run of this project — the data behind the Overview trends.',
    features: [
      { name: 'Snapshots', desc: 'Objects, polygons, file size and structure compliance per run, expandable.' },
      { name: 'Per project', desc: 'Each project keeps its own log (up to 100 runs); clearing it only resets the trends, never the scene.' },
    ],
  },
  'misc-phone': {
    title: 'Read the scene on your phone',
    tagline: 'A QR code opens this UI on your phone — for reading through the scene away from the desk.',
    features: [
      { name: 'Opt-in LAN access', desc: 'Off by default; enabling it binds the server to your local network after a C4D restart.' },
      { name: 'Same UI', desc: 'The phone sees exactly this interface, mobile-adjusted.' },
    ],
    tip: 'Turn it off again when you’re done — while enabled, anyone on your network can reach the tool.',
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
