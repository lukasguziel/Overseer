export type Tone = 'good' | 'mid' | 'low'

// Compliance-Ring (SVG), 0..100
export default function Ring({ pct, tone }: { pct: number; tone?: Tone }) {
  const R = 26; const SW = 7; const C = 2 * Math.PI * R
  const col = tone === 'good' ? 'var(--apply)' : tone === 'mid' ? 'var(--warn)' : 'var(--err)'
  return (
    <svg viewBox="0 0 64 64" className="ring">
      <circle cx="32" cy="32" r={R} fill="none" stroke="var(--panel2)" strokeWidth={SW} />
      <circle cx="32" cy="32" r={R} fill="none" stroke={col} strokeWidth={SW} strokeLinecap="round"
        strokeDasharray={`${pct / 100 * C} ${C}`} transform="rotate(-90 32 32)" />
      <text x="32" y="37" className="ring-text">{pct}%</text>
    </svg>
  )
}
