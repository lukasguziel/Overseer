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
  polys: number
  empty: boolean            // exists but holds no objects
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
  unused: string[]
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
}

export interface TextureReport {
  doc_path: string
  total: number
  absolute_count: number
  relative_count: number
  missing_count: number
  relocatable_count: number
  total_bytes: number    // disk footprint, each physical file counted once
  absolute: TextureEntry[]
  relative: TextureEntry[]
}

export interface SceneReport {
  file: string
  object_count: number
  max_depth: number
  total_polys: number
  total_points: number
  file_size: number
  structure_compliance: number
  analyzed_at?: string
  types: Record<string, number>
  categories: Record<string, number>
  casing: Record<string, number>
  language: Record<string, number>
  nodes: SceneNode[]
  largest?: SceneNode[]
  misplaced?: unknown[]
  materials?: MaterialReport
  textures?: TextureReport
  layers_report?: LayersReport | null
  scoped?: boolean          // true = stats cover only the C4D selection
  hidden_count?: number     // objects hidden in the Object Manager (whole tree)
  include_hidden?: boolean  // false = hidden objects excluded from these stats
  dirty?: number            // C4D change token at read time (auto-refresh sync)
  doc_name?: string         // active document name at read time
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
  compliance?: number
  [key: string]: unknown
}

export interface PresetMeta {
  id: string
  name: string
  description?: string
  created_at?: string
  rules?: number          // number of RuleV2 in the snapshot
  groups?: string[]
}

// Kept as an alias so older call sites keep compiling.
export type Preset = PresetMeta

// ---- Rule engine v2 (config schema 2) ------------------------------------

// A predicate that selects which objects a rule applies to.
export interface MatchJson {
  categories?: Category[]
  keywords?: string[]
  name_regex?: string
  under_group?: string
  types?: string[]
}

export interface RuleBase {
  id: string
  enabled: boolean
  priority: number
}

export interface PrefixRule extends RuleBase {
  type: 'prefix'
  prefix: string
  match: MatchJson
}

export interface RenumberRule extends RuleBase {
  type: 'renumber'
  match: MatchJson
  pad: number
  start: number
  per_parent: boolean
}

export interface ConditionRule extends RuleBase {
  type: 'condition'
  when: { duplicates_gt?: number; match?: MatchJson }
  then: { suffix_scheme?: 'alpha' | 'numeric'; apply_prefix?: string; assign_layer?: string }
}

export interface LayerRule extends RuleBase {
  type: 'layer'
  layer: string
  match: MatchJson
}

export type RuleV2 = PrefixRule | RenumberRule | ConditionRule | LayerRule
export type RuleType = RuleV2['type']

// A node of the nested structure tree (config.structure).
export interface StructureNode {
  name: string
  categories?: string[]
  keywords?: string[]
  aliases?: string[]
  priority?: number
  parent?: string | null   // set by the backend on the flat groups list
  path?: string            // e.g. "Room/Furniture"
  children?: StructureNode[]
}

// config.json schema 2 as read/written through the `config` op.
export interface ConfigV2 {
  schema?: number
  casing?: string
  language?: string | null
  number_pad?: number
  translations?: Record<string, string>
  structure?: StructureNode[]
  rules?: RuleV2[]
  graph?: { nodes: unknown[]; edges: unknown[] }
  preset?: string | null
  [key: string]: unknown
}

// Combined preview returned by plan_all / apply_all.
export interface PlanAllNaming { guid: number; old: string; new: string }
export interface PlanAllStructure { guid: number; name: string; from: string | null; to: string }
export interface PlanAllLayer { guid: number; name: string; layer: string }

export interface PlanAllResult {
  ok?: boolean
  naming: PlanAllNaming[]
  structure: PlanAllStructure[]
  layers: PlanAllLayer[]
  applied_rules: string[]
  warnings: string[]
  total: number
  preset?: string | null
  applied?: { renames: number; reparents: number; layers: number }
}

// Accepted-guid lists a client sends back to apply_all (missing key = accept all).
export interface AcceptLists {
  naming?: number[]
  structure?: number[]
  layers?: number[]
}

export interface RenameDiff {
  guid: number
  old: string
  new: string
}

export interface TranslateDiff extends RenameDiff {
  words?: [string, string][]
  lang?: string           // detected source language of the old name
}

// Detected source-language distribution across the scene (translate.py).
export interface LanguageSummary {
  de: number
  en: number
  unknown: number
  total: number
  dominant: string
}

export interface ReparentDiff {
  name: string
  from: string | null
  to: string
}

export interface LayerDiff {
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
}

export interface GroupRuleJson {
  name: string
  priority: number
  keywords: string[]
  categories: string[]
  aliases: string[]
}

export interface OrganizerSettings {
  casing: string
  language: string | null
  number_pad: number
  selection: boolean
  safe: boolean
  tidy: boolean
}
