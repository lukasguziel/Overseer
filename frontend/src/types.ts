// Typen der Plugin-JSON-API (webapi.py) und des Reports (analyzer.py).

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

export interface Preset {
  id: string
  name: string
  description?: string
  groups?: string[]
}

export interface RenameDiff {
  guid: number
  old: string
  new: string
}

export interface TranslateDiff extends RenameDiff {
  words?: [string, string][]
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

// Plan/Apply-Antworten: plan_* liefert diff+count, apply_* zusaetzlich applied.
export interface PlanResult<D> {
  count: number
  diff?: D[]
  applied?: number
  skipped?: number
  by_layer?: Record<string, number>
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
