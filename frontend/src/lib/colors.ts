// Fixed category colors -> consistent across all charts.
const CATCOLOR: Record<string, string> = {
  light: '#fbbf24', camera: '#38bdf8', mesh: '#34d399',
  spline: '#b07bff', null: '#8b8b93', other: '#64748b',
}
export const catColor = (k: string): string => CATCOLOR[k] || '#64748b'

// Composition strips (casing, language, categories) are NEUTRAL data — a slice
// is a fact, not a verdict. No warn yellow in here: yellow means "todo" system
// wide, and a palette slot must not hand that meaning to whatever class happens
// to land in third place ("mixed" read as an alarm for exactly that reason).
export const STRIP_PALETTE = ['#38bdf8', '#34d399', '#2dd4bf', '#b07bff', '#f472b6', '#8b8b93', '#f5843c']

// Resolution tiers for the texture map: a single-hue RED heat ramp (no scene
// category is red, so a big map never reads as a light/camera/etc.). Small ->
// large runs muted grey -> light salmon -> deep crimson: the heavier the map,
// the hotter and more alarming. Ordered largest-first for threshold matching.
export interface ResTier { label: string; min: number; color: string }
export const RES_TIERS: ResTier[] = [
  { label: '8K+', min: 8192, color: '#8f1d2c' },
  { label: '6K', min: 6144, color: '#c62f34' },
  { label: '4K', min: 4096, color: '#e8553f' },
  { label: '2K', min: 2048, color: '#f0847a' },
  { label: '1K', min: 1024, color: '#f6b8b0' },
  { label: '< 1K', min: 0, color: '#5b6472' },
]
export const resTierColor = (longestPx: number): string =>
  (RES_TIERS.find((t) => longestPx >= t.min) ?? RES_TIERS[RES_TIERS.length - 1]).color
