// Fixed category colors -> consistent across all charts.
const CATCOLOR: Record<string, string> = {
  light: '#fbbf24', camera: '#38bdf8', mesh: '#34d399',
  spline: '#b07bff', null: '#8b8b93', other: '#64748b',
}
export const catColor = (k: string): string => CATCOLOR[k] || '#64748b'

export const STRIP_PALETTE = ['#38bdf8', '#34d399', '#fbbf24', '#b07bff', '#f87171', '#8b8b93', '#f5843c']

// Resolution-tier color: heavier maps run hotter (8K red -> 4K amber ->
// 2K blue -> smaller muted). Same tiers as MaterialsTab's resTier badges.
export const resTierColor = (longestPx: number): string =>
  longestPx >= 8192 ? '#f87171'
    : longestPx >= 4096 ? '#fbbf24'
      : longestPx >= 2048 ? '#38bdf8' : '#5b6472'
