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
  dupTotal: number
  p80: number
  geoObjs: number
  top10pct: number
}

// Derive all hygiene metrics from report.nodes (purely client-side).
export function computeHygiene(nodes: SceneNode[], totalPolys: number): Hygiene {
  const defaults: SceneNode[] = []
  const emptyGroups: SceneNode[] = []
  const rootClutter: SceneNode[] = []
  const outliers: SceneNode[] = []
  const byName: Record<string, SceneNode[]> = {}
  const depth: Record<number, number> = {}
  const thr = Math.max(50000, totalPolys * 0.05)   // outlier: alone >5% of the scene
  for (const n of nodes) {
    depth[n.depth] = (depth[n.depth] || 0) + 1;
    (byName[n.name] = byName[n.name] || []).push(n)
    if (isDefaultName(n.name, n.type)) defaults.push(n)
    if (n.category === 'null' && !n.children) emptyGroups.push(n)
    if (n.depth === 0 && n.category !== 'null') rootClutter.push(n)
    if (n.polygons > thr) outliers.push(n)
  }
  const dupes: DupeEntry[] = Object.entries(byName).filter(([, a]) => a.length > 1)
    .map(([name, a]) => ({ name, count: a.length, guid: a[0].guid }))
    .sort((x, y) => y.count - x.count)
  outliers.sort((a, b) => b.polygons - a.polygons)
  // Pareto: how many objects account for 80% of the polygons?
  const sorted = nodes.filter((n) => n.polygons > 0).map((n) => n.polygons).sort((a, b) => b - a)
  let cum = 0
  let p80 = 0
  for (const v of sorted) { cum += v; p80++; if (cum >= totalPolys * 0.8) break }
  const top10 = sorted.slice(0, 10).reduce((s, v) => s + v, 0)
  const conform = nodes.length - defaults.length - (nodes.length - Object.keys(byName).length)
  return {
    defaults, emptyGroups, rootClutter, outliers, dupes, depth,
    namingScore: nodes.length ? Math.round(Math.max(0, conform) / nodes.length * 100) : 100,
    dupTotal: dupes.reduce((s, d) => s + d.count, 0),
    p80, geoObjs: sorted.length,
    top10pct: totalPolys ? Math.round(top10 / totalPolys * 100) : 0,
  }
}
