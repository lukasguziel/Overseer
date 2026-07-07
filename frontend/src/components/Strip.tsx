import { STRIP_PALETTE } from '../lib/colors'
import { humanNum } from '../lib/format'

type ColorFn = (key: string, index: number) => string

// Duenner 100%-Stacked-Strip + Legende (Composition / Consistency).
export default function Strip({ data, colorFn, format = humanNum, legendMax = 6 }: {
  data: Record<string, number> | undefined
  colorFn?: ColorFn
  format?: (n: number) => string
  legendMax?: number
}) {
  const entries = Object.entries(data || {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])
  const total = entries.reduce((s, [, v]) => s + v, 0)
  if (!total) return <div className="fl-empty">No data.</div>
  const col: ColorFn = colorFn || ((_, i) => STRIP_PALETTE[i % STRIP_PALETTE.length])
  return (
    <div className="strip-wrap">
      <div className="strip">
        {entries.map(([k, v], i) => (
          <div key={k} className="strip-seg" style={{ width: v / total * 100 + '%', background: col(k, i) }}
            title={`${k}: ${format(v)} (${Math.round(v / total * 100)}%)`} />
        ))}
      </div>
      <div className="strip-legend">
        {entries.slice(0, legendMax).map(([k, v], i) => (
          <span key={k} className="strip-key">
            <span className="strip-dot" style={{ background: col(k, i) }} />{k}<b>{Math.round(v / total * 100)}%</b>
          </span>
        ))}
      </div>
    </div>
  )
}
