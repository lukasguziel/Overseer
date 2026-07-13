// Fixed category colors -> consistent across all charts.
const CATCOLOR: Record<string, string> = {
  light: '#fbbf24', camera: '#38bdf8', mesh: '#34d399',
  spline: '#b07bff', null: '#8b8b93', other: '#64748b',
}
export const catColor = (k: string): string => CATCOLOR[k] || '#64748b'

// A C4D layer's own colour (0..1 floats) as a CSS colour — the swatch in the
// layer overview and the one in the no-layer picker must be the same colour, so
// they read the same layer.
export const layerSwatch = (color: [number, number, number] | null | undefined): string => {
  if (!color) return 'var(--dim2)'
  const [r, g, b] = color
  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`
}

// '#rrggbb' -> [r,g,b] as 0..1 floats (C4D layer colors are float vectors).
export function hexToRgb01(hex: string): [number, number, number] {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return [0.5, 0.5, 0.5]
  const v = parseInt(m[1], 16)
  return [((v >> 16) & 255) / 255, ((v >> 8) & 255) / 255, (v & 255) / 255]
}

// n colors evenly spaced along the from->to gradient (sRGB lerp): the first
// layer sits on `from`, the last on `to`. Values are rounded to 3 decimals —
// the same rounding the backend uses when it reads layer colors back, so the
// swatch after a re-analysis is exactly the color that was applied.
export function gradientColors(
  n: number, from: string, to: string,
): [number, number, number][] {
  const a = hexToRgb01(from)
  const b = hexToRgb01(to)
  const out: [number, number, number][] = []
  for (let i = 0; i < n; i++) {
    const t = n <= 1 ? 0 : i / (n - 1)
    out.push([0, 1, 2].map((c) =>
      Math.round((a[c] + (b[c] - a[c]) * t) * 1000) / 1000) as [number, number, number])
  }
  return out
}

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
