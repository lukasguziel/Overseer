export type Tone = 'good' | 'mid' | 'low'

// Compliance ring (SVG), 0..100. Shows the bare number — a score is not a
// percentage in the UI language, just a 0..100 grade.
export default function Ring({ pct, tone, text = true }: { pct: number; tone?: Tone; text?: boolean }) {
  const R = 26; const SW = 7; const C = 2 * Math.PI * R
  const v = Math.max(0, Math.min(100, pct))
  const col = tone === 'good' ? 'var(--apply)' : tone === 'mid' ? 'var(--warn)' : 'var(--err)'
  return (
    <svg viewBox="0 0 64 64" className="ring">
      <circle cx="32" cy="32" r={R} fill="none" stroke="var(--panel2)" strokeWidth={SW} />
      <circle cx="32" cy="32" r={R} fill="none" stroke={col} strokeWidth={SW} strokeLinecap="round"
        strokeDasharray={`${v / 100 * C} ${C}`} transform="rotate(-90 32 32)" />
      {text && <text x="32" y="37" className="ring-text">{v}</text>}
    </svg>
  )
}
