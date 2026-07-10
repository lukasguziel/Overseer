import type { Tone } from '../components/Ring'

// Shared score semantics — ONE place decides how a 0..100 score is judged.
// A score compares open work against the number of objects that exist:
// decided (fixed or accepted-as-is) / total. It is always clamped to 0..100.
export const clampScore = (pct: number): number =>
  Math.max(0, Math.min(100, Math.round(pct)))

export const scoreTone = (pct: number): Tone =>
  pct >= 80 ? 'good' : pct >= 50 ? 'mid' : 'low'

// Qualitative summary shown next to scores: from 80 a scene counts as good
// (tone thresholds and rating words deliberately agree).
export const scoreRating = (pct: number): string =>
  pct >= 95 ? 'Top' : pct >= 80 ? 'Good' : pct >= 50 ? 'Okay' : 'Clean up'
