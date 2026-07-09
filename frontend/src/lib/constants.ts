export const CASINGS: [string, string][] = [
  ['PascalCase', 'PascalCase'],
  ['camelCase', 'camelCase'],
  ['lower_snake', 'lower_snake'],
  ['UPPER_SNAKE', 'UPPER_SNAKE'],
  ['kebab', 'kebab-case'],
]

export const LANGS: [string, string][] = [
  ['en', 'English'],
  ['de', 'German'],
  ['none', 'No translation'],
]

export type TabId =
  | 'overview' | 'assets' | 'naming' | 'translate'
  | 'structure' | 'layers' | 'materials' | 'rules' | 'misc'
  | 'tags' | 'generators' | 'files' | 'sims'

// [id, label, soon?] — `soon` tabs are shown disabled with a "soon" badge.
// Structure & Rules are parked entirely (code stays, nav entry removed) —
// re-add them here to bring them back.
export const TABS: [TabId, string, boolean?][] = [
  ['overview', 'Overview'],
  ['naming', 'Naming'],
  ['translate', 'Translate'],
  ['layers', 'Layers'],
  ['materials', 'Materials'],
  ['assets', 'Assets'],
  ['tags', 'Tags'],
  ['generators', 'Generators'],
  ['files', 'Files'],
  ['sims', 'Sims'],
  ['misc', 'Misc'],
]

// The producible target casings, used to auto-pick the scene's dominant one.
const PRODUCIBLE = CASINGS.map(([v]) => v)

// Most common producible casing in a report.casing distribution, or '' if none
// of the produced styles dominate (scene is mostly Capitalized/mixed/spaced).
export function dominantCasing(dist: Record<string, number> | undefined): string {
  if (!dist) return ''
  let best = ''
  let max = 0
  for (const style of PRODUCIBLE) {
    const n = dist[style] || 0
    if (n > max) { max = n; best = style }
  }
  return best
}

export const CAT_ORDER = ['mesh', 'spline', 'light', 'camera', 'null', 'other']

export const SORTS: [string, string][] = [
  ['polygons', 'Polygons'],
  ['points', 'Points'],
  ['children', 'Children'],
  ['depth', 'Depth'],
  ['name', 'Name'],
  ['layer', 'Layer'],
]

// Small client-side preview of the convention (only for the example display).
export function exampleName(casing: string, pad: number): string {
  const words = ['key', 'light']
  const num = pad > 0 ? String(3).padStart(pad, '0') : '3'
  const cap = (w: string) => w[0].toUpperCase() + w.slice(1)
  switch (casing) {
    case 'PascalCase': return words.map(cap).join('') + num
    case 'camelCase': return words[0] + words.slice(1).map(cap).join('') + num
    case 'lower_snake': return words.join('_') + '_' + num
    case 'UPPER_SNAKE': return words.map((w) => w.toUpperCase()).join('_') + '_' + num
    case 'kebab': return words.join('-') + '-' + num
    default: return ''
  }
}
