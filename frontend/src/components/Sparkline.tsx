// Winzige SVG-Sparkline (Verlauf ueber Analysen).
export default function Sparkline({ data, w = 62, h = 20 }: { data: number[]; w?: number; h?: number }) {
  const min = Math.min(...data)
  const max = Math.max(...data)
  const span = max - min || 1
  const step = data.length > 1 ? w / (data.length - 1) : w
  const pts = data.map((v, i) => `${(i * step).toFixed(1)},${(h - ((v - min) / span) * (h - 3) - 1.5).toFixed(1)}`).join(' ')
  const last = data[data.length - 1]
  const lx = (data.length - 1) * step
  const ly = h - ((last - min) / span) * (h - 3) - 1.5
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} width={w} height={h} preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="1.4"
        strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="1.8" fill="currentColor" />
    </svg>
  )
}
