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
  | 'structure' | 'layers' | 'textures' | 'rules' | 'misc'

export const TABS: [TabId, string][] = [
  ['overview', 'Overview'],
  ['assets', 'Assets'],
  ['naming', 'Naming'],
  ['translate', 'Translate'],
  ['structure', 'Structure'],
  ['layers', 'Layers'],
  ['textures', 'Textures'],
  ['rules', 'Rules'],
  ['misc', 'Misc'],
]

export const CAT_ORDER = ['mesh', 'spline', 'light', 'camera', 'null', 'other']

export const SORTS: [string, string][] = [
  ['polygons', 'Polygons'],
  ['points', 'Points'],
  ['children', 'Children'],
  ['depth', 'Depth'],
  ['name', 'Name'],
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
