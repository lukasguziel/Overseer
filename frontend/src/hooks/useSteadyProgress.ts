import { useRef } from 'react'
import type { ProgressInfo } from '../types'

export interface SteadyProgress {
  phase: string
  pct: number | null // null = indeterminate
  current: number
  total: number
  detail: string
}

// Smooths the raw /api/progress feed for display: within one phase the bar
// never moves backwards (polls can interleave with phase-internal resets),
// while a genuinely new run of the same phase (raw value drops sharply) or a
// phase change resets the bar cleanly. This is what fixes the
// "progress bar runs backwards" glitch in every loading surface.
export default function useSteadyProgress(
  progress: ProgressInfo | null | undefined,
): SteadyProgress | null {
  const last = useRef<{ phase: string; pct: number } | null>(null)
  if (!progress || !progress.active) {
    last.current = null
    return null
  }
  const raw = progress.total > 0
    ? Math.min(100, Math.round(progress.current / progress.total * 100))
    : null
  let pct = raw
  if (raw == null) {
    last.current = null
  } else {
    const prev = last.current
    if (prev && prev.phase === progress.phase && raw < prev.pct) {
      // Small dips are poll jitter → hold. A big drop is a NEW run → reset.
      pct = raw < prev.pct - 25 ? raw : prev.pct
    }
    last.current = { phase: progress.phase, pct: pct as number }
  }
  return {
    phase: progress.phase || 'Working…',
    pct,
    current: progress.current,
    total: progress.total,
    detail: progress.detail,
  }
}
