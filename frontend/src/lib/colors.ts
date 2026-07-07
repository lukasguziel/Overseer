// Fixed category colors -> consistent across all charts.
const CATCOLOR: Record<string, string> = {
  light: '#fbbf24', camera: '#38bdf8', mesh: '#34d399',
  spline: '#b07bff', null: '#8b8b93', other: '#64748b',
}
export const catColor = (k: string): string => CATCOLOR[k] || '#64748b'

export const STRIP_PALETTE = ['#38bdf8', '#34d399', '#fbbf24', '#b07bff', '#f87171', '#8b8b93', '#f5843c']
