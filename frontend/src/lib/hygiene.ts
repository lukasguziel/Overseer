import type { SceneNode } from '../types'

// Generic default names (C4D object types, DE + EN) -> "unnamed".
const DEFAULT_TOKENS = new Set([
  'null', 'cube', 'sphere', 'plane', 'cone', 'cylinder', 'torus', 'disc', 'tube',
  'pyramid', 'platonic', 'figure', 'polygon', 'object', 'spline', 'light', 'camera',
  'floor', 'sky', 'background', 'foreground', 'environment', 'text', 'instance',
  'circle', 'rectangle', 'arc', 'helix', 'star', 'flower', 'cogwheel', 'profile',
  'formula', 'n-side', 'nside', 'vectorizer', 'landscape', 'relief', 'cloner', 'matrix',
  // German
  'wuerfel', 'würfel', 'kugel', 'ebene', 'kegel', 'zylinder', 'licht', 'kamera',
  'objekt', 'boden', 'himmel', 'nullobjekt', 'null-objekt', 'text-spline', 'instanz',
  'kreis', 'rechteck', 'stern', 'landschaft',
])

function baseName(name: string): string {
  return (name || '').replace(/[._\s]*\d+$/, '').trim().toLowerCase()
}

export function isDefaultName(name: string, type?: string): boolean {
  const b = baseName(name)
  if (!b) return true
  if (DEFAULT_TOKENS.has(b)) return true
  const t = (type || '').toLowerCase()
  if (t && (b === t || b.startsWith(t))) return true
  return false
}

// ---- casing (client-side port of sceneorg.naming.casing.detect_casing) ----

const RE_CAMEL = /^[a-z][a-z0-9]*([A-Z][a-z0-9]*)+$/
const RE_PASCAL = /^[A-Z][a-z0-9]*([A-Z][a-z0-9]*)+$/
const RE_UPPER_SNAKE = /^[A-Z0-9]+(_[A-Z0-9]+)+$/
const RE_LOWER_SNAKE = /^[a-z0-9]+(_[a-z0-9]+)+$/

export function detectCasing(name: string): string {
  const base = name.trim()
  if (!base) return 'empty'
  if (base.includes(' ')) return 'spaced'
  if (RE_UPPER_SNAKE.test(base)) return 'UPPER_SNAKE'
  if (RE_LOWER_SNAKE.test(base)) return 'lower_snake'
  if (base.includes('-')) return 'kebab'
  const letters = base.replace(/[^A-Za-zÀ-ÿ]/g, '')
  if (letters && letters === letters.toUpperCase()) return 'UPPER'
  if (letters && letters === letters.toLowerCase()) return 'lower'
  if (RE_CAMEL.test(base)) return 'camelCase'
  if (RE_PASCAL.test(base)) return 'PascalCase'
  if (/^[A-Z]/.test(base) && letters.slice(1) === letters.slice(1).toLowerCase()) return 'Capitalized'
  return 'mixed'
}

// Which detected buckets count as conforming to each producible target
// style. Single words are ambiguous — "Chair" is valid PascalCase, "chair"
// is valid camelCase/lower_snake/kebab — so they credit every style they
// are compatible with instead of punishing clean scenes.
const CASING_COMPAT: Record<string, string[]> = {
  PascalCase: ['PascalCase', 'Capitalized'],
  camelCase: ['camelCase', 'lower'],
  lower_snake: ['lower_snake', 'lower'],
  UPPER_SNAKE: ['UPPER_SNAKE', 'UPPER'],
  kebab: ['kebab', 'lower'],
}

export interface DupeEntry {
  name: string
  count: number
  guid: number
}

export interface Hygiene {
  defaults: SceneNode[]
  emptyGroups: SceneNode[]
  rootClutter: SceneNode[]
  outliers: SceneNode[]
  dupes: DupeEntry[]
  depth: Record<number, number>
  namingScore: number
  casingScore: number
  namingTodos: number
  dupTotal: number
  p80: number
  geoObjs: number
  top10pct: number
}

export interface HygieneOpts {
  // Target casing the user chose ('' = auto: best-fitting producible style).
  casing?: string
  // Names accepted as-is: they never count as todos (defaults, duplicates
  // and casing all included) — the score measures DECISIONS, so a scene
  // where every remaining oddity was deliberately accepted reaches 100.
  kept?: Set<string>
}

// Derive all hygiene metrics from report.nodes (purely client-side).
export function computeHygiene(nodes: SceneNode[], totalPolys: number,
  opts: HygieneOpts = {}): Hygiene {
  const kept = opts.kept
  const isKept = (name: string) => !!kept && kept.has(name)
  const defaults: SceneNode[] = []
  const emptyGroups: SceneNode[] = []
  const rootClutter: SceneNode[] = []
  const outliers: SceneNode[] = []
  const byName: Record<string, SceneNode[]> = {}
  const depth: Record<number, number> = {}
  const buckets: string[] = []
  const thr = Math.max(50000, totalPolys * 0.05)   // outlier: alone >5% of the scene
  for (const n of nodes) {
    depth[n.depth] = (depth[n.depth] || 0) + 1;
    (byName[n.name] = byName[n.name] || []).push(n)
    buckets.push(detectCasing(n.name))
    if (!isKept(n.name) && isDefaultName(n.name, n.type)) defaults.push(n)
    if (n.category === 'null' && !n.children) emptyGroups.push(n)
    if (n.depth === 0 && n.category !== 'null') rootClutter.push(n)
    if (n.polygons > thr) outliers.push(n)
  }
  const dupes: DupeEntry[] = Object.entries(byName)
    .filter(([name, a]) => a.length > 1 && !isKept(name))
    .map(([name, a]) => ({ name, count: a.length, guid: a[0].guid }))
    .sort((x, y) => y.count - x.count)
  outliers.sort((a, b) => b.polygons - a.polygons)

  // Pick the target style: the user's choice, else the best-fitting one.
  const styles = opts.casing && CASING_COMPAT[opts.casing]
    ? [opts.casing]
    : Object.keys(CASING_COMPAT)
  let target = styles[0]
  let best = -1
  for (const s of styles) {
    const ok = buckets.reduce((c, b) => c + (CASING_COMPAT[s].includes(b) ? 1 : 0), 0)
    if (ok > best) { best = ok; target = s }
  }
  const conformSet = new Set(CASING_COMPAT[target])

  // Per-object open todo: default name, duplicate, or off-style casing —
  // unless the name was accepted as-is.
  const dupeNames = new Set(dupes.map((d) => d.name))
  const defaultGuids = new Set(defaults.map((d) => d.guid))
  let todos = 0
  let casingOk = 0
  nodes.forEach((n, i) => {
    const keptName = isKept(n.name)
    const conform = keptName || conformSet.has(buckets[i])
    if (conform) casingOk++
    if (keptName) return
    if (defaultGuids.has(n.guid) || dupeNames.has(n.name) || !conform) todos++
  })

  // Pareto: how many objects account for 80% of the polygons?
  const sorted = nodes.filter((n) => n.polygons > 0).map((n) => n.polygons).sort((a, b) => b - a)
  let cum = 0
  let p80 = 0
  for (const v of sorted) { cum += v; p80++; if (cum >= totalPolys * 0.8) break }
  const top10 = sorted.slice(0, 10).reduce((s, v) => s + v, 0)
  return {
    defaults, emptyGroups, rootClutter, outliers, dupes, depth,
    namingScore: nodes.length ? Math.round((nodes.length - todos) / nodes.length * 100) : 100,
    casingScore: nodes.length ? Math.round(casingOk / nodes.length * 100) : 100,
    namingTodos: todos,
    dupTotal: dupes.reduce((s, d) => s + d.count, 0),
    p80, geoObjs: sorted.length,
    top10pct: totalPolys ? Math.round(top10 / totalPolys * 100) : 0,
  }
}
