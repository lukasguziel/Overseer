// Types of the plugin JSON API (webapi.py) and the report (analyzer.py).

export type Category = 'light' | 'camera' | 'null' | 'mesh' | 'spline' | 'other'

export interface SceneNode {
  guid: number
  name: string
  type: string
  category: Category
  depth: number
  children: number
  polygons: number
  points: number
  visible?: boolean         // Object Manager visibility (editor dot, inherited)
  layer?: string | null     // name of the assigned C4D layer (null = no layer)
}

// One row of the document's layer table (webapi _merge_layers).
export interface LayerInfo {
  name: string
  color: [number, number, number] | null
  solo: boolean
  view: boolean             // editor viewport flag (V)
  render: boolean           // render flag (R)
  locked: boolean           // locked flag (L)
  objects: number           // objects assigned to this layer (scope-aware)
  objects_all?: number      // same, but ALWAYS counting hidden objects too
  materials: number         // materials whose layer link points here
  tags: number              // tags whose layer link points here
  polys: number
  empty: boolean            // NOTHING references it — hidden objects included
}

export interface LayerMismatch {
  guid: number
  name: string
  path: string
  parent: string
  parent_layer: string
  child_layer: string
}

export interface LayersReport {
  layers: LayerInfo[]
  no_layer: number          // objects assigned to no layer at all
  total_layers: number
  empty_layers: number
}

export interface MissingTexture {
  material: string
  file: string
}

export interface MaterialReport {
  total: number
  unused: string[]              // unused + not accepted (the "problem" set)
  only_hidden?: string[]        // used exclusively by hidden objects (own list, protected)
  accepted?: string[]           // accepted-as-unused AND currently unused (for display)
  accepted_all?: string[]       // full accepted-unused set from config (toggle source of truth)
  deletable_count?: number      // unused minus only_hidden (drives the materials score)
  missing: MissingTexture[]
  missing_textures: number
}

export interface TextureEntry {
  material: string
  used: boolean
  file: string           // basename
  path: string           // path as stored in the shader
  resolved: string       // absolute path it resolves to ('' if unresolved)
  absolute: boolean      // stored as an absolute filesystem path
  exists: boolean
  missing: boolean
  relocatable: boolean   // absolute AND file lives under the project folder
  rel_target: string     // the relative path it would become
  bytes: number          // file size on disk (0 if missing/unknown)
  width: number          // pixel dimensions (0 if unknown)
  height: number
  res_tag: string        // resolution tag, e.g. '4K' / '8K' / '512px'
  bit_depth?: number     // bits per channel (0 if unknown)
  channels?: number      // channel count (1 grey … 4 RGBA)
  has_alpha?: boolean    // alpha channel present
  greyscale?: boolean    // single-channel / luminance image
  colorspace?: string    // colorspace tag where readable ('sRGB','linear',…)
  vram?: number          // estimated uncompressed RGBA cost incl. mipmaps (bytes)
  accepted?: boolean     // accepted-as-missing: acknowledged, no longer a problem
}

export interface TextureReport {
  doc_path: string
  total: number
  absolute_count: number
  relative_count: number
  missing_count: number
  relocatable_count: number
  total_bytes: number    // disk footprint, each physical file counted once
  total_vram?: number    // estimated uncompressed RGBA cost incl. mipmaps (bytes)
  absolute: TextureEntry[]
  relative: TextureEntry[]
  accepted?: string[]        // accepted-as-missing paths currently in the scene
  accepted_all?: string[]    // full accepted set from config (restore source)
}

// One external (non-texture) file reference from the files scan (files_scan).
export interface FileEntry {
  kind: string
  file: string
  path: string
  resolved: string
  exists: boolean
  missing: boolean
  absolute: boolean
  relocatable: boolean
  rel_target: string
  bytes: number
  owner: string
  owner_kind?: string   // 'object' | 'material' | '' (take, render data, …)
  guid: number | null
}

export interface FilesScan {
  ok: boolean
  doc_path: string
  entries: FileEntry[]
  accepted?: string[]   // raw paths accepted as missing (keeps section 'files')
  summary: {
    total: number
    by_kind: Record<string, number>
    missing_count: number
    absolute_count: number
    relocatable_count: number
    total_bytes: number
  }
}

export interface SceneReport {
  file: string
  object_count: number
  max_depth: number
  total_polys: number
  total_points: number
  file_size: number
  analyzed_at?: string
  types: Record<string, number>
  categories: Record<string, number>
  casing: Record<string, number>
  language: Record<string, number>
  nodes: SceneNode[]
  largest?: SceneNode[]
  materials?: MaterialReport
  textures?: TextureReport
  textures_error?: string   // set when the texture scan raised (diagnostic)
  layers_report?: LayersReport | null
  scoped?: boolean          // true = stats cover only the C4D selection
  hidden_count?: number     // objects hidden in the Object Manager (whole tree)
  include_hidden?: boolean  // false = hidden objects excluded from these stats
  has_generators?: boolean  // scene has at least one audited generator (else Generators tab is disabled)
  has_sims?: boolean        // scene has at least one simulation participant (else Sims tab is disabled)
  dirty?: number            // C4D change token at read time (auto-refresh sync)
  doc_name?: string         // active document name at read time
  sel?: number              // selection token at read time (selection-scope sync)
}

// Live progress of a long-running main-thread operation (GET /api/progress,
// answered by the bridge's server thread while the main thread is busy).
export interface ProgressInfo {
  active: boolean
  phase: string
  current: number
  total: number
  detail: string
}

export interface DetectInfo {
  style: string
  language: string | null
  number_pad: number
  confidence: number
}

export interface HistoryEntry {
  file: string
  at: string
  ts: number
  objects: number
  polys?: number
  size?: number
  [key: string]: unknown
}

// One field change of one object inside a batched tool mutation.
export interface ChangeItem {
  sid?: number              // C4D-stable object id (for revert; absent for texpath)
  name: string              // object name after the change (revert fallback match)
  field: 'name' | 'layer' | 'parent' | 'texpath'
  before: string
  after: string
  reverted?: boolean        // this single op has been reverted (per-op revert)
}

// One batched tool mutation (one apply = one entry), newest first from the API.
export interface ChangeEntry {
  id: string
  ts: number
  at: string                // "YYYY-MM-DD HH:MM:SS"
  kind: string              // naming | structure | layers | translate | materials_delete | textures_relative
  summary: string
  doc?: string
  items: ChangeItem[]
  revertible: boolean
  reverted: boolean
}

export interface RenameDiff {
  guid: number
  old: string
  new: string
  rules?: string[]   // every naming rule that produced it: casing | numbering | unique
}

export interface TranslateDiff extends RenameDiff {
  words?: [string, string][]
  lang?: string           // detected source language of the old name
}

// Detected source-language distribution across the scene (translate.py).
export interface LanguageSummary {
  counts: Record<string, number>  // lang code ('de','fr','ru','en',…) -> objects
  total: number
  dominant: string
  // legacy convenience keys (still sent by the backend)
  de: number
  en: number
  unknown: number
}

export interface LayerDiff {
  guid: number
  name: string
  layer: string
}

// Plan/apply responses: plan_* returns diff+count, apply_* additionally applied.
export interface PlanResult<D> {
  count: number
  diff?: D[]
  applied?: number
  skipped?: number
  by_layer?: Record<string, number>
  detected?: LanguageSummary   // translate: detected source-language spread
  target?: string              // translate: chosen target language
  engine?: string              // translate: 'offline' (dictionaries) | 'google'
  kept?: string[]              // keys the user accepted as-is (config keeps)
}

export interface OrganizerSettings {
  casing: string
  apply_casing: boolean
  keep_separators: boolean
  keep_specials: boolean
  language: string | null
  number_pad: number
  apply_numbering: boolean
  dedupe: boolean
  selection: boolean
  include_hidden: boolean
}
